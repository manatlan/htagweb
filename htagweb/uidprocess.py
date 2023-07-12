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

logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.INFO)

logger = logging.getLogger(__name__)

def mainprocess(uid,timeout, input,output):
    print("Process Start",uid)

    hts={}

    class SesHT:
        def __init__(self,session):
            self.session = session

        async def ping(self, msg):
            self.session["ping"]="here"
            return f"hello {msg}"

        #==========================================================
        async def ht_create(self, fqn,js,init_params=None,renew=False):        # -> str
        #==========================================================
            """ HRenderer creator """
            self.session["ht_create"]="here"
            if init_params is None : init_params=((),{})

            #--------------------------- fqn -> module, name
            names = fqn.split(".")
            modulename,name=".".join(names[:-1]), names[-1]
            module=importlib.import_module(modulename)
            #---------------------------
            htClass = getattr(module,name)

            hr=hts.get(fqn)
            if renew or (hr is None) or str(init_params)!=str(hr.init):
                ##HRenderer(tagClass: type, js:str, exit_callback:Optional[Callable]=None, init= ((),{}), fullerror=False, statics=[], session=None ):
                hr=HRenderer( htClass,
                        js=js,
                        session=self.session,
                        init= init_params,
                )
                hts[fqn] = hr
            return str(hr)


        #==========================================================
        async def ht_interact(self,fqn,data): # -> dict
        #==========================================================
            """ interact with hrenderer instance """
            self.session["ht_interact"]="here"
            hr=hts[fqn]

            #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\ to simplify ut
            if data["id"]=="ut":
                data["id"] = id(hr.tag) #only main tag ;-(
            #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\

            x = await hr.interact(data['id'],data['method'],data['args'],data['kargs'],data.get('event') )

            self.session = hr.session
            return x

    async def loop():
        while input.poll(timeout=timeout):
            session,action,(a,k) = input.recv()
            if action=="quit":
                break

            ss=SesHT(session)

            method=getattr(ss,action)
            r=await method(*a,**k)

            output.send( (ss.session,r) )

    asyncio.run( loop() )
    print("Process Stop",uid)

clone = lambda x: json.loads(json.dumps(x))

class UidProcess:

    def __init__(self,uid:str,session:dict,timeout=600):
        self.session = session
        qs,qr=multiprocessing.Pipe()
        rs,rr=multiprocessing.Pipe()
        self.input=qs
        self.output=rr

        ps = multiprocessing.Process(target=mainprocess, args=[uid,timeout,qr,rs])
        ps.start()

    def quit(self):
        self.input.send( ({},"quit",([],{}) ))

    def __getattr__(self,action:str):
        def _(*a,**k):
            cses = clone(self.session)  #TODO really needed ?!?
            # cses = self.session
            try:
                self.input.send( (cses,action,(a,k)))
            except Exception as e:
                return e

            try:
                cses,o= self.output.recv()
            except Exception as e:
                return e

            if isinstance(o,Exception):
                return o
            else:
                self.session.update(cses)

                return o
        return _


class Users:
    _users = {}

    @classmethod
    def use(cls,uid):
        if uid not in cls._users:
            cls._users[uid] = UidProcess( uid, {} )
        return cls._users[uid]

    @classmethod
    def kill(cls):
        for key,up in cls._users.items():
            up.quit()

    @classmethod
    def all(cls):
        return list(cls._users.keys())

if __name__=="__main__":
    u1=Users.use("u1")
    print( u1.session )
    u1.ping("jjj")
    print( u1.session )

    u2=Users.use("u2")
    print( u2.session )
    u2.ping("jjj")
    print( u2.session )


    Users.kill()