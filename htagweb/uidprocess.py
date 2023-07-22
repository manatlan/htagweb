# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################
import asyncio,sys
import multiprocessing
import logging,importlib
from htag.render import HRenderer
from shared_memory_dict import SharedMemoryDict

logger = logging.getLogger(__name__)

def mainprocess(uid,session,timeout, input,output):
    logger.info("Process Start for %s",uid)

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

            hr=HTS.get(fqn)
            if renew or (hr is None) or str(init_params)!=str(hr.init):
                ##HRenderer(tagClass: type, js:str, exit_callback:Optional[Callable]=None, init= ((),{}), fullerror=False, statics=[], session=None ):

                #--------------------------- fqn -> module, name
                names = fqn.split(".")
                modulename,name=".".join(names[:-1]), names[-1]
                if modulename in sys.modules:
                    module=sys.modules[modulename]
                    try:
                        module=importlib.reload( module )
                    except ModuleNotFoundError:
                        """ can't be (really) reloaded if the component is in the
                        same module as the instance htag server"""
                        pass
                else:
                    module=importlib.import_module(modulename)
                #---------------------------
                htClass = getattr(module,name)


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
            try:
                if action=="_quit_":
                    r="_quit_"
                    break

                ss=Actions()
                method=getattr(ss,action)
                try:
                    r=await method(*a,**k)
                except Exception as e:
                    r=e
            finally:
                output.send( r )

    asyncio.run( loop() )
    logger.info("Process ended for %s",uid)

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

    def is_alive(self):
        return self._ps and self._ps.is_alive()

    def quit(self):
        if self.is_alive():
            self._quit_()
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
        if uid in cls._users:
            ps=cls._users[uid]
            if ps.is_alive():
                cls._users[uid] = ps
            else:
                cls._users[uid] = UidProcess( uid )
        else:
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
        #TODO: currently it returns all users which have existed (during gunicorn session)
        #TODO: it could test if they are alive or not ?!
        return list(cls._users.keys())

if __name__=="__main__":
    u1=Users.use("u1")
    u1.ping("jjj")
    print( u1.session )

    u2=Users.use("u2")
    u2.ping("jjj")
    print( u2.session )


    Users.killall()
