from dataclasses import dataclass
from pathlib import Path
from typing import List
from typing import Iterable

@dataclass
class CommandSpec:
    name: str
    command: Iterable[str]
    delay: int = 10

@dataclass
class InfodConfig:
    debug_log: bool
    debug_fuse: bool
    mountpoint: Path
    commands: List[CommandSpec]
