# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import asyncio,traceback
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
CMD_RENDER="RENDER"

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
def process(hid:Hid,js,init,sesprovidername,force):
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

        # register hid in redys "apps"
        await bus.sadd(KEYAPPS,str(hid))

        # save sesprovider for this hid
        await bus.set(hid.key_sesprovider, FactorySession.__name__)


        session = FactorySession(hid.uid)

        styles=Tag.style("body.htagoff * {cursor:not-allowed !important;}")

        hr=HRenderer( klass ,js, init=init, exit_callback=suicide, fullerror=True, statics=[styles,],session = session)

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

        while RRR:
            params = await bus.get_event( hid.event_interact )
            if params is not None:  # sometimes it's not a dict ?!? (bool ?!)
                if params.get("cmd") == CMD_EXIT:
                    break
                elif params.get("cmd") == CMD_RENDER:
                    # just a false start, just need the current render
                    log("RERENDER")
                    hr.session = FactorySession(hid.uid)    # reload session
                    assert await bus.publish(hid.event_response,str(hr))
                else:
                    log("INTERACT")
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
        assert await bus.unsubscribe( hid.event_interact )

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

    ps={}

    async def killall(ps:dict):
        # try to send a EXIT CMD to all running ps
        for hid,infos in ps.items():
            ps[hid]["process"].kill()
            # remove hid in redys "apps"
            await bus.srem(KEYAPPS,hid)


    while 1:
        params = await bus.get_event( EVENT_SERVER )
        if params is not None:
            if params.get("cmd") == CMD_EXIT:
                log(EVENT_SERVER, params.get("cmd") )
                break
            elif params.get("cmd") == "CLEAN":
                log(EVENT_SERVER, params.get("cmd") )
                await killall(ps)
                continue

            hid:Hid=params["hid"]
            key_init=str(params["init"])

            #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
            # TODO: this code will be changed soon ;-)
            #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
            shid=hid.hid
            if shid in ps and ps[shid]["process"].is_alive():
                # process is already running

                if params["force"] or key_init != ps[shid]["key"]:
                    # kill itself because it's not the same init params, or force recreate
                    if params["force"]:
                        log("Destroy/Recreate a new process (forced)",hid)
                    else:
                        log("Destroy/Recreate a new process (qp changed)",hid)
                    ps[shid]["process"].kill()

                    # remove hid in redys "apps"
                    await bus.srem(KEYAPPS,str(hid))

                    # and recreate another one later
                else:
                    # it's the same initialization process

                    log("Reuse process",hid)
                    # so ask process to send back its render
                    assert await bus.publish(hid.event_interact,dict(cmd=CMD_RENDER))
                    continue
            else:
                log("Start a new process",hid)

            # create the process
            p=multiprocessing.Process(target=process, args=[],kwargs=params)
            p.start()

            # and save it in pool ps
            ps[shid]=dict( process=p, key=key_init, event_interact=hid.event_interact)
            #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\

        await asyncio.sleep(0.1)

    assert await bus.unsubscribe( EVENT_SERVER )

    await killall(ps)

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
        await asyncio.sleep(0.5)


async def kill_hrserver():
    bus=redys.v2.AClient()
    await bus.publish( EVENT_SERVER, dict(cmd=CMD_EXIT) )   # kill orchestrator loop


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
