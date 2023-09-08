# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################
from ..usot import Usot


class ServerDict: # proxy between app and ServerUnique
    def __init__(self,uid,dico:dict):
        self._uid=uid
        self._dico=dico

    def items(self):
        return self._dico.items()

    def get(self,k:str,default=None):       # could be inplemented in SessionMem
        return self._dico.get(k,default)

    def __getitem__(self,k:str):            # could be inplemented in SessionMem
        return self._dico[k]

    def __setitem__(self,k:str,v):          # could be inplemented in SessionMem
        self._dico[k]=v
        PX.clientsync.set( self._uid, self._dico)

    def clear(self):
        self._dico.clear()
        PX.clientsync.set( self._uid, {})

    def __repr__(self):
        return f"<SessionMem {self._dico}>"


class SessionMemory: # unique source of truth handled by ServerUnique
    def __init__(self):
        self.SESSIONS={}
    def get(self,uid:str) -> ServerDict:
        if uid not in self.SESSIONS:
            self.SESSIONS[uid] = {}
        return ServerDict( self, uid, self.SESSIONS[uid] )
    def set(self,uid:str,dico):
        self.SESSIONS[uid] = dico

PX=Usot( SessionMemory, port=19999 )
PX.start()                                              #<- so it's ALWAYS runned as task (on ip:port)

async def create(uid) -> ServerDict:
    return await PX.clientsync.get( uid )