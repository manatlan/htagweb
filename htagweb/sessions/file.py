# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import os,pickle,tempfile

from collections import UserDict
class FileDict(dict): # default
    """ mimic a dict (with minimal methods), unique source of truth, based on FS"""
    def __init__(self,uid:str,persistent:bool=False):
        self._uid=uid
        if persistent:
            name=""
        else:
            name=f"{os.getppid()}-"
        self._file=os.path.join( tempfile.gettempdir(), f"htagweb_{name}{uid}.ses" )

        if os.path.isfile(self._file):
            with open(self._file,"rb+") as fid:
                d=pickle.load(fid)
        else:
            d={}

        super().__init__( d )

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
            with open(self._file,"wb+") as fid:
                pickle.dump(dict(self),fid, protocol=4)
        else:
            if os.path.isfile(self._file):
                os.unlink(self._file)


class FilePersistentDict(FileDict): # default
    def __init__(self,uid):
        FileDict.__init__(self,uid,persistent=True)
