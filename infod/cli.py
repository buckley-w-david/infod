from pathlib import Path

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

data_home = xdg_data_home() / Path('infod/mnt')
config_home = xdg_config_home() / Path('infod/config.toml')

@app.command()
def serve(mountpoint: Path = data_home, config: Path = config_home, debug: bool = False, debug_fuse: bool = False):
    mountpoint.mkdir(exist_ok=True)

    config = toml.load(config)
    infod_config = InfodConfig(
        mountpoint=mountpoint,
        commands=[CommandSpec(**command) for command in config[ 'Commands' ]],
        debug_log=debug,
        debug_fuse=debug_fuse
    )

    logging.init_logging(infod_config.debug_log)
    info_filesystem = InfoFs(infod_config)
    info_filesystem.serve()

if __name__ == '__main__':
    app()
