# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htag
# #############################################################################

from shared_memory_dict import SharedMemoryDict

def session(uid):
    """ create session dict"""
    return SharedMemoryDict(name=uid, size=10024)   #TODO: fix number

def wses():
    """ Get the global smd WSES (which handles uid:lastaccess'datetime)"""
    return SharedMemoryDict(name="WSES", size=10024)    #TODO: fix number

