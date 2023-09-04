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
        self._s=o
        self._uid=uid
        self._d=self._s.get(uid)

    def items(self):
        return self._d.items()

    def get(self,k:str,default=None):
        return self._d.get(k,default)

    def __getitem__(self,k:str):
        return self._d[k]

    def __setitem__(self,k:str,v):
        self._d[k]=v
        self._s.set( self._uid , self._d)

    def clear(self):
        self._d.clear()
        self._s.set( self._uid , {})

su=None
def create(uid) -> SessionMem:
    global su
    su = ServeUnique( SessionMemory, port=19999 )
    su.start()
    return SessionMem(su, uid)
