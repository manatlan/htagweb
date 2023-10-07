# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import asyncio,traceback,os
from more_itertools import last
import redys
import redys.v2
import os,sys,importlib,inspect
import multiprocessing
from htag import Tag
from htag.render import HRenderer

import logging
logger = logging.getLogger(__name__)


EVENT_SERVER="EVENT_SERVER"

CMD_EXIT="EXIT"
CMD_REUSE="RENDER"

KEYAPPS="htagweb.apps"

def importClassFromFqn(fqn_norm:str) -> type:
    assert ":" in fqn_norm
    #--------------------------- fqn -> module, name
    modulename,name = fqn_norm.split(":",1)
    if modulename in sys.modules:
        module=sys.modules[modulename]
        try:
            module=importlib.reload( module )
        except ModuleNotFoundError as e:
            """ can't be (really) reloaded if the component is in the
            same module as the instance htag server"""
            print("*WARNING* can't force module reload:",e)
    else:
        module=importlib.import_module(modulename)
    #---------------------------
    klass= getattr(module,name)
    if not ( inspect.isclass(klass) and issubclass(klass,Tag) ):
        raise Exception(f"'{fqn_norm}' is not a htag.Tag subclass")

    if not hasattr(klass,"imports"):
        # if klass doesn't declare its imports
        # we prefer to set them empty
        # to avoid clutering
        klass.imports=[]
    return klass

def importFactorySession( sesprovidername=None ):
    import htagweb.sessions
    return getattr(htagweb.sessions,sesprovidername or "MemDict")

class Hid:
    def __init__(self,hid:str):
        uid,fqn=hid.split("_",1)
        self.uid=uid
        self.fqn=fqn
        self.hid=hid

        self.event_interact = "interact_"+hid
        self.event_interact_response = self.event_interact+"_response"

        self.event_response = "response_"+hid
        self.event_response_update = self.event_response+"_update"

        self.key_sesprovider = "sesprovider_"+hid

    @staticmethod
    def create(uid:str,fqn:str):
        return Hid(uid+"_"+fqn)

    def __str__(self):
        return self.hid
    def __repr__(self):
        return self.hid

##################################################################################
def process(hid:Hid,js,init,sesprovidername):
##################################################################################
    FactorySession=importFactorySession(sesprovidername)

    pid = os.getpid()

    def log(*a):
        txt=f">PID {pid} {hid}: %s" % (" ".join([str(i) for i in a]))
        print(txt,flush=True,file=sys.stdout)
        logger.info(txt)

    async def loop():
        RRR={"1":"1"} #TODO: find something better ;-)

        def suicide():
            log("suicide")
            RRR.clear()

        bus = redys.v2.AClient()
        try:
            if os.getcwd() not in sys.path: sys.path.insert(0,os.getcwd())
            klass=importClassFromFqn(hid.fqn)
        except Exception as e:
            log("importClassFromFqn ERROR",traceback.format_exc())
            #TODO: do better here
            assert await bus.publish(hid.event_response,str(e))
            return

        last_mod_time=os.path.getmtime(inspect.getfile(klass))

        # register hid in redys "apps"
        await bus.sadd(KEYAPPS,str(hid))

        # save sesprovider for this hid
        await bus.set(hid.key_sesprovider, FactorySession.__name__)


        session = FactorySession(hid.uid)

        styles=Tag.style("body.htagoff * {cursor:not-allowed !important;}")

        hr=HRenderer( klass ,js, init=init, exit_callback=suicide, fullerror=True, statics=[styles,],session = session)

        key_init=str(init)

        log(f"Start with params:",init)

        # subscribe for interaction
        await bus.subscribe( hid.event_interact )

        # publish the 1st rendering
        assert await bus.publish(hid.event_response,str(hr))

        # register tag.update feature
        #======================================
        async def update(actions):
            try:
                r=await bus.publish(hid.event_response_update,actions)
            except:
                log("!!! concurrent write/read on redys !!!")
                r=False
            return r

        hr.sendactions=update
        #======================================
        recreate={}

        while RRR:
            params = await bus.get_event( hid.event_interact )
            if params is not None:  # sometimes it's not a dict ?!? (bool ?!)
                if params.get("cmd") == CMD_EXIT:
                    log("Exit explicit")
                    recreate={}
                    break   # <- destroy itself
                elif params.get("cmd") == CMD_REUSE:
                    # event REUSE
                    params=params.get("params")
                    if str(params['init'])!=key_init or os.path.getmtime(inspect.getfile(klass))!=last_mod_time:
                        # ask server/orchestrator to recreate me
                        log("RECREATE")
                        recreate=dict(
                                    hid=hid,                                    # reuse current
                                    js=js,                                      # reuse current
                                    init= params["init"],                       # use new
                                    sesprovidername=FactorySession.__name__,    # reuse current
                                )
                        break   # <- destroy itself
                    else:
                        log("REUSE")
                        recreate={}
                        hr.session = FactorySession(hid.uid)    # reload session
                        assert await bus.publish(hid.event_response,str(hr))
                else:
                    log("INTERACT")
                    recreate={}
                    #-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\- UT
                    if params["oid"]=="ut": params["oid"]=id(hr.tag)
                    #-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-

                    actions = await hr.interact(**params)

                    # always save session after interaction
                    hr.session._save()

                    assert await bus.publish(hid.event_interact_response,actions)

            await asyncio.sleep(0.1)

        # remove hid in redys "apps"
        await bus.srem(KEYAPPS,str(hid))

        # delete sesprovider for this hid
        await bus.delete(hid.key_sesprovider)

        #consume all pending events
        await bus.unsubscribe( hid.event_interact )

        if recreate:
            assert await bus.publish( EVENT_SERVER , recreate )


    asyncio.run( loop() )
    log("end")



##################################################################################
async def hrserver_orchestrator():
##################################################################################
    bus=redys.v2.AClient()

    def log(*a):
        txt=f"-ORCHESTRATOR- %s" % (" ".join([str(i) for i in a]))
        print(txt,flush=True,file=sys.stdout)
        logger.info(txt)


    # prevent multiple orchestrators
    if await bus.get("hrserver_orchestrator_running")==True:
        log("already running")
        return
    else:
        log("started")
        await bus.set("hrserver_orchestrator_running",True)

    # register its main event
    await bus.subscribe( EVENT_SERVER )

    async def killall():
        # try to send a EXIT CMD to all running ps
        running_hids = await bus.get(KEYAPPS) or []
        while running_hids:
            for hid in running_hids:
                await bus.publish(Hid(hid).event_interact,dict(cmd=CMD_EXIT))
            running_hids = await bus.get(KEYAPPS) or []
            await asyncio.sleep(0.1)

    while 1:
        params = await bus.get_event( EVENT_SERVER )
        if params is not None:
            if params.get("cmd") == CMD_EXIT:
                log(EVENT_SERVER, params.get("cmd") )
                break
            elif params.get("cmd") == "CLEAN":
                log(EVENT_SERVER, params.get("cmd") )
                await killall()
                continue

            hid:Hid=params["hid"]

            running_hids:list=await bus.get(KEYAPPS) or []
            if str(hid) in running_hids:
                log("Try to reuse process",hid)
                assert await bus.publish(hid.event_interact,dict(cmd=CMD_REUSE,params=params))
            else:
                p=multiprocessing.Process(target=process, args=[],kwargs=params)
                p.start()
                log("Start a new process",hid,"in",p.pid)

        await asyncio.sleep(0.1)

    assert await bus.unsubscribe( EVENT_SERVER )

    await bus.set("hrserver_orchestrator_running",False)

    await killall()

    log("stopped")

async def wait_redys():
    bus=redys.v2.AClient()
    while 1:
        try:
            if await bus.ping()=="pong":
                break
        except:
            pass
        await asyncio.sleep(0.1)


##################################################################################
class ServerClient:
##################################################################################
    """ to expose server features """
    def __init__(self):
        self._bus=redys.v2.AClient()

    async def list(self) -> list:
        """ list all process uid&fqn """
        ll = sorted(await self._bus.get(KEYAPPS))
        return [Hid(hid) for hid in ll]

    async def kill(self,hid:Hid):
        """ kill a process (process event)"""
        await self._bus.publish(hid.event_interact,dict(cmd=CMD_EXIT))

    async def killall(self):
        """ killall process (server event)"""
        await self._bus.publish(EVENT_SERVER,dict(cmd="CLEAN"))

    async def session(self,hid:Hid) -> dict:
        """ get session for hid"""
        sesprovidername=await self._bus.get(hid.key_sesprovider)
        FactorySession=importFactorySession(sesprovidername)
        return FactorySession(hid.uid)


async def wait_hrserver():
    bus=redys.v2.AClient()
    while 1:
        try:
            if await bus.get("hrserver_orchestrator_running"):
                break
        except Exception as e:
            print(e)
        await asyncio.sleep(0.1)


async def kill_hrserver():
    bus=redys.v2.AClient()
    await bus.publish( EVENT_SERVER, dict(cmd=CMD_EXIT) )   # kill orchestrator loop

    await asyncio.sleep(1)


##################################################################################
async def hrserver():
##################################################################################
    s=redys.v2.Server()
    s.start()

    await wait_redys()

    await hrserver_orchestrator()

    s.stop()




if __name__=="__main__":
    asyncio.run( hrserver() )
