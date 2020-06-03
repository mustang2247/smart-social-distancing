import pathlib
import tempfile
from typing import NamedTuple

from . import ROOT_DIR
from .config import get_config

_host = lambda host: '' if host is None else f' DOCKER_HOST=ssh://{host}'
_target = lambda target: '' if target is None else f' --target {target}'
_tag = lambda tag: '' if tag is None else f' -t {tag}'  # tag
_rm = lambda rm: '' if rm is None else ' --rm'  # remove after use
_it = lambda it: '' if it is None else ' -it'  # interactive
_runtime = lambda runtime: '' if runtime is None else f' --runtime {runtime}'
_cache_from = lambda cache_from: '' if cache_from is None else f' --cache-from {cache_from}'
_privileged = lambda privileged: '' if privileged is None else ' --privileged'
_entrypoint = lambda entrypoint: '' if entrypoint is None else f' --entrypoint {entrypoint}'
_command = lambda command: '' if command is None else f' {command}'
_config = lambda config: '' if config is None else f' --config {config}'
_dockerfile = lambda dockerfile: '' if dockerfile is None else f' -f {dockerfile}'
listable = lambda func: lambda x: ''.join(map(func, x)) if isinstance(x, (list, tuple)) else func(
    x)  # allow single item or list of multiple items
_p = listable(lambda p: '' if p is None else (f' -p {p}' if ':' in str(p) else f' -p {p}:{p}'))  # port mapping
_v = listable(lambda v: '' if v is None else (f' -v {v}' if ':' in str(v) else f' -v {v}:{v}'))  # volume mount
_e = listable(lambda e: '' if e is None else f' -e {e}')  # environment variable


class PipedDockerfile(NamedTuple):
    command: str


def build(c, dockerfile=None, image=None, target=None, host=None, cache_from=None):
    if isinstance(dockerfile, PipedDockerfile):
        pipe_cmd = f' {dockerfile.command} |'
        dockerfile = '-'  # read from stdin
    else:
        pipe_cmd = ''

    with c.cd(ROOT_DIR):
        c.run(
            f'{pipe_cmd}{_host(host)} docker '
            f'build{_target(target)}{_tag(image)}{_cache_from(cache_from)} '
            f'-f {dockerfile} .'
        )


def login(c):
    c.run('mkdir -p ~/.neuralet-dev/docker')
    c.run('docker --config ~/.neuralet-dev/docker login')


def push(c, image, host=None, config=None):
    c.run(f'{_host(host)} docker{_config(config)} push {image}')


def pull(c, image, host=None, config=None):
    c.run(f'{_host(host)} docker{_config(config)} pull {image}')


def run(c, image, rm=None, it=None, p=None, host=None, v=None, runtime=None, e=None, privileged=None, entrypoint=None,
        command=None):
    c.run(
        f'{_host(host)} docker'
        f' run{_runtime(runtime)}{_rm(rm)}{_it(it)}{_p(p)}{_v(v)}{_e(e)}{_privileged(privileged)}{_entrypoint(entrypoint)}'
        f' {image}{_command(command)}'
    )


def tag(c, source_image, target_image, host=None):
    c.run(f'{_host(host)} docker tag {source_image} {target_image}')


def get_image_tag(c, name, public_image=False, version='latest'):
    image_name = get_config(c, 'docker.image_name' if public_image else 'docker.private_image_name')
    tag_suffix = get_config(c, 'docker.tag_suffixes')[name]
    return f'{image_name}:{version}{tag_suffix}'


def get_host(c, name, local):
    return None if local else get_config(c, 'docker.default_host')[name]


def get_dockerfile(c, name):
    return get_config(c, 'docker.dockerfiles')[name]


def dockerfile_replace_from_public_with_private(c, dockerfile):
    image_name = get_config(c, 'docker.image_name').replace('/', '\/')  # quote for running in bash
    public_image_name = get_config(c, 'docker.private_image_name').replace('/', '\/')  # quote for running in bash
    return PipedDockerfile(f'cat {dockerfile} | sed -e "s/\(--from=\){image_name}\([: ]\)/\\1{public_image_name}\\2/"')


def auto_build(c, name, local=False, public_image=False, **kwargs):
    image = get_image_tag(c, name, public_image)
    # kwargs.setdefault('cache_from', image)
    kwargs.setdefault('host', get_host(c, name, local))
    kwargs.setdefault('image', image)
    kwargs.setdefault('target', get_config(c, 'docker.custom_targets').get(name, None))
    dockerfile = get_dockerfile(c, name)
    if not public_image:
        dockerfile = dockerfile_replace_from_public_with_private(c, dockerfile)
    return build(c, dockerfile, **kwargs)


def auto_push(c, name, local=False, public_image=False, **kwargs):
    kwargs.setdefault('host', get_host(c, name, local))
    kwargs.setdefault('image', get_image_tag(c, name, public_image))
    push(c, **kwargs)


def auto_pull(c, name, local=False, public_image=False, **kwargs):
    kwargs.setdefault('host', get_host(c, name, local))
    kwargs.setdefault('image', get_image_tag(c, name, public_image))
    pull(c, **kwargs)


def auto_run(c, name, local=False, public_image=False, **kwargs):
    kwargs.setdefault('image', get_image_tag(c, name, public_image))
    kwargs.setdefault('host', get_host(c, name, local))
    kwargs.setdefault('runtime', get_config(c, 'docker.custom_runtimes').get(name, None))
    run(c, **kwargs)
