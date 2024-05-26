# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2024 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################
import json
import aiofiles

from .hrprocess import process
from .fifo import Fifo

import multiprocessing

def startHrProcess(uid,moduleapp,timeout_inactivity):
    """ return '' if ok, or the start error """
    queue = multiprocessing.Queue()
    p=multiprocessing.Process(target=process, args=[queue,uid,moduleapp,timeout_inactivity],kwargs={},daemon=True)
    p.start()
    p.join(timeout=0.2)
    return p,queue.get()


class HrClient:
    def __init__(self,uid:str, moduleapp:str, timeout_interaction:int=60, timeout_inactivity:int=None):
        self._fifo=Fifo(uid,moduleapp,timeout_interaction)
        self.timeout_inactivity=timeout_inactivity or 0

    async def updater(self):
        async with aiofiles.open(self._fifo.UPDATE_FIFO, mode='r') as fifo_update:
            while 1:
                async for message in fifo_update:
                    yield json.loads( message.strip() )

    def log(self,*a):
        msg = " ".join([str(i) for i in ["hrclient",self._fifo,":"] + list(a)])
        # logging.warning( msg )
        RED='\033[0;32m'
        NC='\033[0m' # No Color        
        print(RED,msg,NC,flush=True)


    async def create(self, js:str, init=None) -> str:
        # Assurez-vous que les pipes existent
        if self._fifo.exists():
            self.log("reuse fifo process")
        else:
            self.log("start fifo process")
            self._process, err = startHrProcess(self._fifo.uid,self._fifo.moduleapp,self.timeout_inactivity)
            if err:
                raise Exception(err)

        self._html = await self._fifo.com("create",init=init, js=js,fullerror=False)
        return self._html

    def __str__(self) -> str:
        return self._html

    async def interact(self,id:int,method:str,args:list,kargs:dict,event=None) -> dict:
        if self._fifo.exists():
            return await self._fifo.com("interact",id=id,method=method,args=args,kargs=kargs,event=event)
        else:
            raise Exception( f"App {self._fifo} is NOT RUNNING ! (can't interact)")

    async def exit(self):
        if self._fifo.exists():
            # kill softly
            assert await self._fifo.com("exit")
            self._process.kill()
        else:
            raise Exception( f"App {self._fifo} is NOT RUNNING ! (can't exit)")

    @classmethod
    async def clean(cls):
        for f in Fifo.childs():
            print(f"Client '{f}' is running, will kill it")
            # kill hardly
            f.destroy()

