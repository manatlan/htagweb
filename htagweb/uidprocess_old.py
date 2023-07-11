# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htag
# #############################################################################
import asyncio
import multiprocessing
import threading
import queue
import logging,importlib
import traceback
from htag.render import HRenderer

logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.INFO)

logger = logging.getLogger(__name__)




def uidprocess(uid,session,queues, timeout = 10*60):
    hts={}
    qin,qout = queues

    #==========================================================
    async def ping(msg):
    #==========================================================
        """ just for UT """
        return f"hello {msg}"

    #==========================================================
    async def ht_create(fqn,js,init_params=None,renew=False):        # -> str
    #==========================================================
        """ HRenderer creator """
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
                    session=session,
                    init= init_params,
            )
            hts[fqn] = hr
        return str(hr)


    #==========================================================
    async def ht_interact(fqn,data): # -> dict
    #==========================================================
        """ interact with hrenderer instance """
        hr=hts[fqn]

        #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\ to simplify ut
        if data["id"]=="ut":
            data["id"] = id(hr.tag) #only main tag ;-(
        #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\

        return await hr.interact(data['id'],data['method'],data['args'],data['kargs'],data.get('event') )


    methods=locals()

    async def processloop():
        #process loop
        while 1:
            try:
                action,(a,k) = qin.get(timeout=timeout)
            except queue.Empty:
                logger.info("Process %s: inactivity timeout (%ssec)",uid,timeout)
                break
            # except OSError:
            #     logger.info("Process %s: breaks",uid)
            #     break

            qout.put("ok")

            if action=="quit":
                break
            else:
                try:
                    method=methods[action]
                    logger.info("Process %s: %s",uid,action)
                    r=await method(*a,**k)

                    qout.put( dict(result=r) )
                except Exception as e:
                    logger.error("Process %s: ERROR '%s'",uid,e)
                    qout.put( dict(error=traceback.format_exc(),exception=e) )


    asyncio.run( processloop() )
    qin.close()
    qout.close()
    logger.info("Process %s: ended",uid)

# https://stackoverflow.com/questions/18213619/sharing-a-lock-between-gunicorn-workers?rq=1
# https://docs.gunicorn.org/en/latest/design.html



class UidProxyException(Exception): pass
class UidProxy:
    PP = {}

    def __init__(self,uid, session, timeout:float = 10*60 ):
        reuse=uid in UidProxy.PP
        if reuse:
            p,qin,qout=UidProxy.PP[uid]
            reuse = p.is_alive()

        if reuse:
            logger.info("UidProxy: reuse process %s",uid)
        else:
            logger.info("UidProxy: start process %s",uid)
            qin=multiprocessing.Queue()
            qout=multiprocessing.Queue()

            # p=multiprocessing.Process( target=uidprocess, args=(uid, session, (qin,qout), timeout), name=f"process {uid}" )
            p=threading.Thread( target=uidprocess, args=(uid, session, (qin,qout)), name=f"process {uid}" )
            p.start()
            UidProxy.PP[uid]=p,qin,qout

        self.qin=qin
        self.qout=qout
        self.uid=uid

    def quit(self):
        """ quit process of this uid """
        self.qin.put( ('quit',( (),{} )) )
        if self.uid in UidProxy.PP:
            del UidProxy.PP[self.uid]
        self.qin.close()
        self.qout.close()

    @classmethod
    def shutdown(cls):
        """ terminate all UidProxy' process"""
        for uid in list(cls.PP.keys()):
            UidProxy(uid,{}).quit() #TODO: pas bo du tout !!!!!

    def _com(self,action,*a,**k):
        """ SYNC COM ! """
        logger.info(">> UidProxy: com %s(%s,%s)",action,a,k)

        # send request
        try:
            self.qin.put( (action,(a,k)) )
        except Exception:
            return UidProxyException(f"queue is closed") # in this process !

        # wait a confirmation (to test ps is alive)
        try:
            x=self.qout.get(timeout=0.5)    # minimal response
            assert x=="ok"
        except Exception:
            return UidProxyException(f"queue is closed on process side") # in the other process !

        # wait the real response
        x:dict=self.qout.get(timeout=30)
        if "error" in x:
            return UidProxyException(f"UidProxy action '{action}' -> {x['error']}")
        else:
            r=x["result"]
            logger.info("<< UidProxy: com %s << %s",action,hasattr(r,"__len__") and len(r) or r)
            return r

    def __getattr__(self,action:str):
        async def _(*a,**k):
            return self._com( action, *a,**k )
        return _


#/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\


#~ async def main():


    #~ p1=UidProxy("u1")
    #~ try:
        #~ fakefile = lambda f: os.path.isfile(f) and Request(dict(method="GET",type="http",path=f,headers={}))

        #~ x=await p1.exec( fakefile("../pscom_api.py") )
        #~ print(x.status_code, x.body)

    #~ finally: # needed if exception in try/catch --> we shutdown all process
        #~ UidProxy.shutdown()

#~ if __name__=="__main__":
    #~ asyncio.run( main() )
