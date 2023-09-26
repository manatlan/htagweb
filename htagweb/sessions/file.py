# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import os,pickle,tempfile


class FileDict: # default
    """ mimic a dict (with minimal methods), unique source of truth, based on FS"""
    def __init__(self,uid:str,persistent:bool):
        self._uid=uid
        if persistent:
            name=""
        else:
            name=f"{os.getppid()}-"
        self._file=os.path.join( tempfile.gettempdir(), f"htagweb_{name}{uid}.ses" )

        if os.path.isfile(self._file):
            with open(self._file,"rb+") as fid:
                self._d=pickle.load(fid)
        else:
            self._d={}

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

        with open(self._file,"wb+") as fid:
            pickle.dump(self._d,fid, protocol=4)

    def __setitem__(self,k:str,v):
        """ save session """
        self._d[k]=v

        with open(self._file,"wb+") as fid:
            pickle.dump(self._d,fid, protocol=4)

    def clear(self):
        """ save session """
        self._d.clear()
        if os.path.isfile(self._file):
            os.unlink(self._file)

async def create(uid,persistent=False) -> FileDict:
    return FileDict(uid,persistent)
