# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################
from ..proxysingleton import ProxySingleton
import asyncio

class SessionMem: # proxy between app and ServerUnique
    def __init__(self,dico:dict):
        self._dico=dico
        # self._save=cb

    def items(self):
        return self._dico.items()

    def get(self,k:str,default=None):       # could be inplemented in SessionMem
        return self._dico.get(k,default)

    def __getitem__(self,k:str):            # could be inplemented in SessionMem
        return self._dico[k]

    def __setitem__(self,k:str,v):          # could be inplemented in SessionMem
        self._dico[k]=v
        # asyncio.create_task( self._save(self._dico ))

    def clear(self):
        self._dico.clear()
        # asyncio.create_task( self._save( {}))

    def __repr__(self):
        return f"<SessionMem {self._dico}>"


class SessionMemory: # unique source of truth handled by ServerUnique
    def __init__(self):
        self.SESSIONS={}
    def get(self,uid:str) -> SessionMem:
        if not uid in self.SESSIONS:
            self.SESSIONS[uid] = SessionMem( {} )
        return self.SESSIONS[uid]


su=None #NOT TOP ;-)
async def create(uid) -> SessionMem:
    global su
    su = ProxySingleton( SessionMemory, port=19999 )
    return await su.get( uid )
