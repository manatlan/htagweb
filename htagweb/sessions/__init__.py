# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

def createFile(uid):
    from . import file
    file.create(uid)

def createFilePersistent(uid): # <- persistent after server reboot
    from . import file
    file.create(uid,True)

def createShm(uid):
    from . import shm
    shm.create(uid)

def createMem(uid):
    from . import memory
    memory.create(uid)

__all__= ["createFile","createFilePersistent","createShm","createMem"]