# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

async def createFile(uid):
    from .file import FileDict
    return FileDict(uid)

async def createFilePersistent(uid): # <- persistent after server reboot
    from .file import FilePersistentDict
    return FilePersistentDict(uid)

#DEPRECATED
async def createShm(uid):
    from . import shm
    return await shm.create(uid)

async def createMem(uid):
    from .mem import MemDict
    return MemDict(uid)

__all__= ["createFile","createFilePersistent","createShm","createMem"]