# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################
from ..serverunique import ServerUnique

class SessionMemory:
    def __init__(self):
        self.SESSIONS={}
    def get(self,uid:str):
        return self.SESSIONS.get(uid,{})
    def set(self,uid:str,value:dict):
        assert isinstance(value,dict)
        self.SESSIONS[uid]=value

class SessionMem:
    def __init__(self,server,uid:str):
        self._s=server
        self._uid=uid

    def _load(self) -> dict:
        return self._s.get(self._uid)
    def _save(self,d:dict):
        self._s.set( self._uid , d)

    def items(self):
        return self._load().items()

    def get(self,k:str,default=None):
        return self._load().get(k,default)

    def __getitem__(self,k:str):
        return self._load()[k]

    def __setitem__(self,k:str,v):
        d=self._load()
        d[k]=v
        self._save(d)

    def clear(self):
        self._save({})

su=None #NOT TOP ;-)
def create(uid) -> SessionMem:
    global su
    su = ServeUnique( SessionMemory, port=19999 )
    su.start()
    return SessionMem(su, uid)
