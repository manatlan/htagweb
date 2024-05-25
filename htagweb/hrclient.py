# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import asyncio
import json
import sys
import subprocess
import aiofiles
import inspect

#TODO: to be runnable as is ;-(
#TODO: move this tests in pytest, one day ! (and not be runnable as is !!!)
try:
    from . import hrprocess
    from .fifo import Fifo
except ImportError:
    from htagweb import hrprocess
    from htagweb.fifo import Fifo



class HrClient:
    def __init__(self,uid:str, moduleapp:str, timeout_interaction:int=60, timeout_inactivity:int=None):
        self._fifo=Fifo(uid,moduleapp,timeout_interaction)
        self.timeout_inactivity=timeout_inactivity or 0

    async def updater(self):
        async with aiofiles.open(self._fifo.UPDATE_FIFO, mode='r') as fifo_update:
            while 1:
                async for message in fifo_update:
                    yield json.loads( message.strip() )

    async def create(self, js:str, init=None) -> str:
        # Assurez-vous que les pipes existent
        if self._fifo.exists():
            print("Client: reuse",self._fifo)
            feedback="ok"
        else:
            # TODO: the way to spawn the process is particular ;-)
            hrprocess_py = inspect.getabsfile( hrprocess )
            cmds=[sys.executable,hrprocess_py,self._fifo.uid,self._fifo.moduleapp,str(self.timeout_inactivity) ]
            print("Client: run",self._fifo)
            # ps=subprocess.Popen(cmds)
            # await asyncio.sleep(1)
            # feedback="ok"
            ps=subprocess.Popen(cmds,stdout=subprocess.PIPE,bufsize=0)
            feedback=ps.stdout.readline().decode().strip()
            if feedback!="ok":
                raise Exception(feedback)

        h = await self._fifo.com("create",init=init, js=js,fullerror=False)
        self._html =h
        return h

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
        else:
            raise Exception( f"App {self._fifo} is NOT RUNNING ! (can't exit)")

    @classmethod
    async def clean(cls):
        for f in Fifo.childs():
            print(f"Client '{f}' is running, will kill it")
            # kill hardly
            f.destroy()


if __name__=="__main__":
    import pytest
    async def main():
        hr=HrClient("ut1","main")
        with pytest.raises(Exception):
            await hr.create("//ddd")

        hr=HrClient("ut1","main.AppUnknown")
        with pytest.raises(Exception):
            await hr.create("//ddd")

        hr=HrClient("ut1","main:App")
        with pytest.raises(Exception):
            await hr.create("//ddd")

        hr=HrClient("ut1","mainUnknown.AppUnknown")
        with pytest.raises(Exception):
            await hr.create("//ddd")

        hr=HrClient("ut1","examples.simple.App")
        html = await hr.create("//ddd")
        assert "<!DOCTYPE html>" in html
        assert "function action" in html

    async def runner():
        await main()
        await HrClient.clean()

    asyncio.run( runner() )