# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import os,pickle

def create(uid):
    return SessionFile(uid)

class SessionFile: # default
    """ mimic a dict (with minimal methods), unique source of truth"""
    def __init__(self,uid:str):
        self._uid=uid
        self._file=f"uid_{uid}.ses"

        if os.path.isfile(self._file):
            with open(self._file,"rb+") as fid:
                self._d=pickle.load(fid)
        else:
            self._d={}

    def items(self):
        return self._d.items()

    def get(self,k:str,default=None):
        return self._d.get(k,default)

    def __getitem__(self,k:str):
        return self._d[k]

    def __setitem__(self,k:str,v):
        self._d[k]=v

        with open(self._file,"wb+") as fid:
            pickle.dump(self._d,fid)

    def clear(self):
        self._d.clear()
        with open(self._file,"wb+") as fid:
            pickle.dump(self._d,fid)