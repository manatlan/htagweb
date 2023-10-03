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

class MemDict: # default
    """ mimic a dict (with minimal methods), unique source of truth, based on redys.v2"""
    def __init__(self,uid:str):
        self._uid=uid
        self._bus=redys.v2.Client()
        self._d=self._bus.get(self._uid) or {}

    def __len__(self):
        return len(self._d.keys())

    def __contains__(self,key):
        return key in self._d.keys()

    def items(self):
        return self._d.items()

    def get(self,k:str,default=None):
        return self._d.get(k,default)

    def __getitem__(self,k:str):
        return self._d[k]

    def __delitem__(self,k:str):
        """ save session """
        del self._d[k]
        self._bus.set(self._uid, self._d)

    def __setitem__(self,k:str,v):
        """ save session """
        self._d[k]=v
        self._bus.set(self._uid, self._d)

    def clear(self):
        """ save session """
        self._d.clear()
        self._bus.delete(self._uid)

