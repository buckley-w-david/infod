from pathlib import Path
import subprocess
import typing

import toml
import typer
from xdg import (
    xdg_config_home,
    xdg_data_dirs,
    xdg_data_home,
)

from infod.filesystem import InfoFs
from infod import logging
from infod.config import InfodConfig, CommandSpec

app = typer.Typer()

default_mount = xdg_data_home() / Path('infod/mnt')
default_config = xdg_config_home() / Path('infod/config.toml')

@app.command()
def serve(config: Path = default_config, mountpoint: typing.Optional[Path] = typer.Argument(None), debug: bool = False, debug_fuse: bool = False):
    config = toml.load(config)
    if not mountpoint:
        mountpoint = Path(config.get('mountpoint', default_mount))
    mountpoint.mkdir(parents=True, exist_ok=True)

    try:
        clean(mountpoint)
    except:
        pass

    infod_config = InfodConfig(
        mountpoint=mountpoint,
        commands=[CommandSpec(**command) for command in config[ 'Commands' ]],
        debug_log=debug,
        debug_fuse=debug_fuse
    )

    logging.init_logging(infod_config.debug_log)
    info_filesystem = InfoFs(infod_config)
    info_filesystem.serve()

@app.command()
def clean(mountpoint: Path = default_mount):
    subprocess.run(['fusermount', '-u', mountpoint])

if __name__ == '__main__':
    app()
