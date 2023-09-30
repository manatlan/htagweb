# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

async def createFile(uid):
    from . import file
    return await file.create(uid)

async def createFilePersistent(uid): # <- persistent after server reboot
    from . import file
    return await file.create(uid,True)

async def createShm(uid):
    from . import shm
    return await shm.create(uid)

__all__= ["createFile","createFilePersistent","createShm"]