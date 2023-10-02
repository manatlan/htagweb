# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

# DEPRECATED
async def create(uid,size=10240):
    # need to install "shared_memory_dict" (py>=3.8)
    from shared_memory_dict import SharedMemoryDict
    return SharedMemoryDict(name=uid, size=10240)