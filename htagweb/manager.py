# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htag
# #############################################################################
import sys
import asyncio
import multiprocessing
from .uidprocess import UidProxy
import logging

logger = logging.getLogger(__name__)

def mainprocess(input,output):
    print("MAINPROCESS")

    async def ping(msg):
        return f"hello {msg}"

    async def exec(uid,session,request):
        p=UidProxy(uid,session)
        return await p.exec(request)

    async def ht_create(uid,session,fqn,js,init_params=None,renew=False):
        p=UidProxy(uid,session)
        return await p.ht_create(fqn,js,init_params,renew)

    async def ht_interact(uid,session,fqn,data):
        p=UidProxy(uid,session)
        return await p.ht_interact(fqn,data)

    methods=locals()

    async def loop():
        while 1:
            action,(a,k) = input.recv()
            print("::: RECV=",action,file=sys.stdout,flush=True)
            if action=="quit":
                break

            method=methods[action]
            # logger.info("Process %s: %s",uid,action)
            r=await method(*a,**k)

            output.send( r )

    asyncio.run( loop() )
    UidProxy.shutdown()
    print("MAINPROCESS EXITED")


class Manager:
    _p=multiprocessing.Manager().dict()

    def __init__(self):
        if not Manager._p:
            qs,qr=multiprocessing.Pipe()
            rs,rr=multiprocessing.Pipe()
            Manager._p["input"]=qs
            Manager._p["output"]=rr

            ps = multiprocessing.Process(target=mainprocess, args=[qr,rs])
            ps.start()

        self.pp=Manager._p

    def shutdown(self):
        if self.pp:
            self.pp["input"].send( ("quit",([],{}) ))
            self.pp=None
            Manager._p={}

    def __getattr__(self,action:str):
        def _(*a,**k):
            self.pp["input"].send( (action,(a,k)))

            return self.pp["output"].recv()
        return _
