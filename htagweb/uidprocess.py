# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htag
# #############################################################################
import asyncio,sys
import multiprocessing
import threading
import json
import logging,importlib
import traceback
from htag.render import HRenderer
from shared_memory_dict import SharedMemoryDict

logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.INFO)

logger = logging.getLogger(__name__)

def mainprocess(uid,session,timeout, input,output):
    print("Process Start",uid,flush=True)

    HTS={}

    class Actions:
        async def ping(self, msg):
            session["ping"]="here"
            return f"hello {msg}"

        #==========================================================
        async def ht_create(self, fqn,js,init_params=None,renew=False):        # -> str
        #==========================================================
            """ HRenderer creator """
            session["ht_create"]="here"
            if init_params is None : init_params=((),{})

            #--------------------------- fqn -> module, name
            names = fqn.split(".")
            modulename,name=".".join(names[:-1]), names[-1]
            module=importlib.import_module(modulename)
            #---------------------------
            htClass = getattr(module,name)

            hr=HTS.get(fqn)
            if renew or (hr is None) or str(init_params)!=str(hr.init):
                ##HRenderer(tagClass: type, js:str, exit_callback:Optional[Callable]=None, init= ((),{}), fullerror=False, statics=[], session=None ):
                hr=HRenderer( htClass,
                        js=js,
                        session=session,
                        init= init_params,
                )
                HTS[fqn] = hr
            return str(hr)


        #==========================================================
        async def ht_interact(self,fqn,data): # -> dict
        #==========================================================
            """ interact with hrenderer instance """
            session["ht_interact"]="here"
            hr=HTS[fqn]

            #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\ to simplify ut
            if data["id"]=="ut":
                data["id"] = id(hr.tag) #only main tag ;-(
            #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\

            x = await hr.interact(data['id'],data['method'],data['args'],data['kargs'],data.get('event') )

            return x

    async def loop():
        while input.poll(timeout=timeout):
            action,(a,k) = input.recv()
            if action=="quit":
                break

            ss=Actions()
            method=getattr(ss,action)
            try:
                r=await method(*a,**k)
            except Exception as e:
                r=e

            output.send( r )

    asyncio.run( loop() )
    print("Process Stop",uid,flush=True)

class UidProcess:

    def __init__(self,uid:str,timeout=600):
        self.uid = uid
        self.session = SharedMemoryDict(name=self.uid, size=10024)   #TODO: fix number

        qs,qr=multiprocessing.Pipe()
        rs,rr=multiprocessing.Pipe()
        self.input=qs
        self.output=rr

        self._ps = multiprocessing.Process(target=mainprocess, args=[uid,self.session,timeout,qr,rs])
        self._ps.start()

    def quit(self):
        if self._ps and self._ps.is_alive():
            self.input.send( ("quit",([],{}) ))
            self.session.shm.close()
            self.session.shm.unlink()
            del self.session
            self._ps.join()
            self._ps=None

    def __getattr__(self,action:str):
        def _(*a,**k):
            try:
                self.input.send( (action,(a,k)))
            except Exception as e:
                return e

            try:
                o= self.output.recv()
            except Exception as e:
                return e

            return o   # return object or exception
        return _


class Users:
    _users = {}

    @classmethod
    def use(cls,uid):
        if uid not in cls._users:
            cls._users[uid] = UidProcess( uid )
        return cls._users[uid]

    @classmethod
    def get(cls,uid):
        return cls._users[uid]

    @classmethod
    def killall(cls):
        for key,up in cls._users.items():
            up.quit()

    @classmethod
    def all(cls):
        return list(cls._users.keys())

if __name__=="__main__":
    u1=Users.use("u1")
    u1.ping("jjj")
    print( u1.session )

    u2=Users.use("u2")
    u2.ping("jjj")
    print( u2.session )


    Users.killall()
