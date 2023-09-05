# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################
from ..proxysingleton import ProxySingleton

class SessionMemory: # unique source of truth handled by ServerUnique
    def __init__(self):
        self.SESSIONS={}
    def get(self,uid:str):
        return self.SESSIONS.get(uid,{})
    def set(self,uid:str,value:dict):
        assert isinstance(value,dict)
        self.SESSIONS[uid]=value

class SessionMem: # proxy between app and ServerUnique
    def __init__(self,su:ProxySingleton,uid:str):
        self._su=su
        self._uid=uid

    def _load(self) -> dict:
        return self._su.get( self._uid )
    def _save(self,d:dict):
        self._su.set( self._uid , d )

    def items(self):
        return self._load().items()

    def get(self,k:str,default=None):       # could be inplemented in SessionMem
        return self._load().get(k,default)

    def __getitem__(self,k:str):            # could be inplemented in SessionMem
        return self._load()[k]

    def __setitem__(self,k:str,v):          # could be inplemented in SessionMem
        d=self._load()
        d[k]=v
        self._save(d)

    def clear(self):
        self._save({})

su=None #NOT TOP ;-)
def create(uid) -> SessionMem:
    global su
    su = ProxySingleton( SessionMemory, port=19999 )
    return SessionMem(su, uid)
