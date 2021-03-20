import os
import sys
from argparse import ArgumentParser
import stat
import logging
import errno
import pyfuse3
import trio

import itertools

import faulthandler

faulthandler.enable()
log = logging.getLogger(__name__)

from dataclasses import dataclass
import typing

@dataclass
class InfoFile:
    name: bytes
    content: bytes
    inode: int

class InfoFs(pyfuse3.Operations):
    def __init__(self, infod_config):
        self.mountpoint = infod_config.mountpoint
        self.debug = infod_config.debug_fuse
        self.commands = infod_config.commands
        self.info_files = [
            InfoFile(
                name=bytes(spec.name, 'utf-8'),
                content=b'',
                inode=pyfuse3.ROOT_INODE+1+i
            ) for (i, spec) in enumerate(infod_config.commands)
        ]

        self.files_by_name = {
            info_file.name: info_file for info_file in self.info_files
        }
        self.files_by_inode = {
            info_file.inode: info_file for info_file in self.info_files
        }

        super(InfoFs, self).__init__()

    async def getattr(self, inode, ctx=None):
        entry = pyfuse3.EntryAttributes()
        if inode == pyfuse3.ROOT_INODE:
            entry.st_mode = (stat.S_IFDIR | 0o755)
            entry.st_size = 0
        elif inode in self.files_by_inode:
            entry.st_mode = (stat.S_IFREG | 0o644)
            entry.st_size = len(self.files_by_inode[inode].content)
        else:
            raise pyfuse3.FUSEError(errno.ENOENT)

        entry.st_ino = inode
        stamp = int(1438467123.985654 * 1e9) # WTF
        # now_ns = int(time() * 1e9)
        entry.st_atime_ns = stamp
        entry.st_ctime_ns = stamp
        entry.st_mtime_ns = stamp
        entry.st_gid = os.getgid()
        entry.st_uid = os.getuid()

        return entry

    async def lookup(self, parent_inode, name, ctx=None):
        if parent_inode != pyfuse3.ROOT_INODE or name not in self.files_by_name:
            raise pyfuse3.FUSEError(errno.ENOENT)
        return await self.getattr(self.files_by_name[name].inode)

    async def opendir(self, inode, ctx):
        if inode != pyfuse3.ROOT_INODE:
            raise pyfuse3.FUSEError(errno.ENOENT)
        return inode

    async def readdir(self, inode, off, token):
        assert inode == pyfuse3.ROOT_INODE

        if off < len(self.info_files):
            info_file = self.info_files[off]
            pyfuse3.readdir_reply(
                token, info_file.name, await self.getattr(info_file.inode), off+1)

    async def open(self, inode, flags, ctx):
        if inode not in self.files_by_inode:
            raise pyfuse3.FUSEError(errno.ENOENT)
        if flags & os.O_RDWR or flags & os.O_WRONLY:
            raise pyfuse3.FUSEError(errno.EACCES)
        return pyfuse3.FileInfo(fh=inode)

    async def read(self, fh, off, size):
        assert fh in self.files_by_inode
        data = self.files_by_inode[fh].content
        if data is None:
            data = b''
        return data[off:off+size]

    async def _scheduler(self, name, command, delay, nursery):
        process = await trio.run_process(command, capture_stdout=True)
        info_file = self.files_by_name[name]
        info_file.content = process.stdout

        await trio.sleep(delay)
        nursery.start_soon(self._scheduler, name, command, delay, nursery)

    async def _go(self):
        fuse_options = set(pyfuse3.default_options)
        fuse_options.add('fsname=infofs')
        if self.debug:
            fuse_options.add('debug')
        pyfuse3.init(self, str(self.mountpoint), fuse_options)

        try:
            async with trio.open_nursery() as nursery:
                nursery.start_soon(pyfuse3.main)
                for command_spec in self.commands:
                    nursery.start_soon(
                        self._scheduler,
                        bytes(command_spec.name, 'utf-8'),
                        command_spec.command,
                        command_spec.delay,
                        nursery
                    )
        except:
            raise
        finally:
            pyfuse3.close()

    def serve(self):
        trio.run(self._go)
