# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import asyncio,traceback,os
import signal
import redys
import redys.v2
import os,sys,importlib,inspect
import multiprocessing
from htag import Tag
from htag.render import HRenderer

import logging
logger = logging.getLogger(__name__)

# input command in hrprocess
CMD_PS_EXIT="EXIT"
CMD_PS_REUSE="REUSE"

# output command from hrprocess to hrclient
CMD_RESP_RENDER="RENDER"
CMD_RESP_RECREATE="RECREATE"

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

        self.key_sesinfo = "sesprovider_"+hid

    @staticmethod
    def create(uid:str,fqn:str):
        return Hid(uid+"_"+fqn)

    def __str__(self):
        return self.hid
    def __repr__(self):
        return self.hid

##################################################################################
def hrprocess(hid:Hid,js,init,sesprovidername,useUpdate):
##################################################################################
    FactorySession=importFactorySession(sesprovidername)

    pid = os.getpid()

    def log(*a):
        txt=f">PID {pid} {hid}: %s" % (" ".join([str(i) for i in a]))
        print(txt,flush=True,file=sys.stdout)
        logger.info(txt)

    async def loop():
        running={"1":"1"} #TODO: find something better ;-)

        def suicide():
            log("suicide")
            running.clear()

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


        session = FactorySession(hid.uid)

        styles=Tag.style("body.htagoff * {cursor:not-allowed !important;}")

        hr=HRenderer( klass ,js, init=init, exit_callback=suicide, fullerror=True, statics=[styles,],session = session)

        key_init=str(init)

        log(f"Start with params:",init)

        # register hid in redys "apps"
        await bus.sadd(KEYAPPS,str(hid))

        # save sesprovider for this hid
        await bus.set(hid.key_sesinfo, dict(sesprovider=FactorySession.__name__, pid=pid))

        # subscribe for interaction
        await bus.subscribe( hid.event_interact )

        # publish the 1st rendering
        assert await bus.publish(hid.event_response,dict( cmd=CMD_RESP_RENDER,render=str(hr)))

        # register tag.update feature
        #======================================
        async def update(actions):
            """ return always True !!
                IRL: it should wait an hrclient response to return true/false according
                the fact it reachs to send back on socket.
            """
            try:
                await bus.publish(hid.event_response_update,actions)
            except:
                log("!!! concurrent write/read on redys !!!")
            return True
        if useUpdate:
            log("tag.update enabled")
            hr.sendactions=update
        else:
            log("tag.update not possible (http only)")
        #======================================
        recreate={}

        while running:
            params = await bus.get_event( hid.event_interact )
            if params is not None:  # sometimes it's not a dict ?!? (bool ?!)
                if params.get("cmd") == CMD_PS_EXIT:
                    log("Exit explicit")
                    recreate={}
                    break   # <- destroy itself
                elif params.get("cmd") == CMD_PS_REUSE:
                    # event REUSE
                    params=params.get("params")
                    if str(params['init'])!=key_init or os.path.getmtime(inspect.getfile(klass))!=last_mod_time:
                        # ask hrclient to destroy/recreate me
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
                        can = await bus.publish(hid.event_response,dict( cmd=CMD_RESP_RENDER, render=str(hr)))
                        if not can:
                            log("Can't answer the response for the REUSE !!!!")
                else:
                    log("INTERACT")
                    recreate={}
                    #-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\- UT
                    if params["oid"]=="ut": params["oid"]=id(hr.tag)
                    #-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-

                    actions = await hr.interact(**params)

                    # always save session after interaction
                    hr.session._save()

                    can = await bus.publish(hid.event_interact_response,actions)
                    if not can:
                        log("Can't answer the interact_response for the INTERACT !!!!")

            await asyncio.sleep(0.1)

        # remove hid in redys "apps"
        await bus.srem(KEYAPPS,str(hid))

        # delete sesprovider for this hid
        await bus.delete(hid.key_sesinfo)

        #consume all pending events
        await bus.unsubscribe( hid.event_interact )

        if recreate:
            assert await bus.publish( hid.event_response , dict(cmd=CMD_RESP_RECREATE,params=recreate) )


    asyncio.run( loop() )
    log("end")




async def killall():
    """ killall running hrprocess (soft and hard if it can't)"""
    bus=redys.v2.AClient()

    # try to send a EXIT CMD to all running ps
    while 1:
        running_hids = await bus.get(KEYAPPS) or []
        if not running_hids:
            break
        else:
            for hid in running_hids:
                # try a soft kill (tell him to suicide itself)
                can = await bus.publish(Hid(hid).event_interact,dict(cmd=CMD_PS_EXIT))
                if not can:
                    # force kill by using its pid
                    sesinfo = await bus.get(hid.key_sesinfo)
                    pid=sesinfo["pid"]
                    print("killall() FORCE KILL",hid,"on pid",pid, flush=True)
                    try:
                        os.kill(pid, signal.SIGKILL)

                        # remove hid in redys "apps"
                        await bus.srem(KEYAPPS,str(hid))

                        # delete sesprovider for this hid
                        await bus.delete(hid.key_sesinfo)

                        #consume all pending events
                        await bus.unsubscribe( hid.event_interact )

                    except ProcessLookupError:
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
        await self._bus.publish(hid.event_interact,dict(cmd=CMD_PS_EXIT))

    async def killall(self):
        """ killall processes"""
        await killall()

    async def session(self,hid:Hid) -> dict:
        """ get session for hid"""
        sesinfo=await self._bus.get(hid.key_sesinfo)
        sesprovidername=sesinfo["sesprovider"]
        FactorySession=importFactorySession(sesprovidername)
        return FactorySession(hid.uid)


##################################################################################
async def startServer():
##################################################################################
    # start a redys server (only one will win)
    s=redys.v2.ServerProcess()

    # wait redys up
    bus=redys.v2.AClient()
    while 1:
        try:
            if await bus.ping()=="pong":
                break
        except:
            pass
        await asyncio.sleep(0.1)

    return s


##################################################################################
async def stopServer(s):
##################################################################################
    # clean all running process
    await killall()

    # before stopping
    s.stop()


if __name__=="__main__":
    # asyncio.run( hrserver() )
    pass
