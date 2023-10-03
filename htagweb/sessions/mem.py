# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import os,pickle,tempfile
import redys.v2

from collections import UserDict
class MemDict(dict): # default
    """ mimic a dict (with minimal methods), unique source of truth, based on redys.v2"""
    def __init__(self,uid:str):
        self._uid=uid
        self._bus=redys.v2.Client()
        super().__init__( self._bus.get(self._uid) or {} )

    def __delitem__(self,k:str):
        super().__delitem__(k)
        self._save()

    def __setitem__(self,k:str,v):
        super().__setitem__(k,v)
        self._save()

    def clear(self):
        super().clear()
        self._save()

    def _save(self):
        if len(self):
            self._bus.set(self._uid, dict(self))
        else:
            self._bus.delete(self._uid)

