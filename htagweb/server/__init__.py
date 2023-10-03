# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import asyncio
import redys
import redys.v2
import os,sys,importlib,inspect
import multiprocessing
from htag import Tag
from htag.render import HRenderer



EVENT_SERVER="EVENT_SERVER"

CMD_EXIT="EXIT"
CMD_RENDER="RENDER"

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



def process(uid,hid,event_response,event_interact,fqn,js,init,sesprovidername):
    #''''''''''''''''''''''''''''''''''''''''''''''''''''
    if sesprovidername is None:
        sesprovidername="MemDict"
    import htagweb.sessions
    FactorySession=getattr(htagweb.sessions,sesprovidername)
    #''''''''''''''''''''''''''''''''''''''''''''''''''''

    pid = os.getpid()
    async def loop():
        with redys.v2.AClient() as bus:
            try:
                if os.getcwd() not in sys.path: sys.path.insert(0,os.getcwd())
                klass=importClassFromFqn(fqn)
            except Exception as e:
                print(f">Process {pid} ERROR :",hid,e)
                #TODO: do better here
                assert await bus.publish(event_response,str(e))
                return

            RUNNING=True
            def exit():
                RUNNING=False

            session = FactorySession(uid)

            styles=Tag.style("body.htagoff * {cursor:not-allowed !important;}")

            hr=HRenderer( klass ,js, init=init, exit_callback=exit, fullerror=True, statics=[styles,],session = session)

            print(f">Process {pid} started with :",hid,init)


            # subscribe for interaction
            await bus.subscribe( event_interact )

            # publish the 1st rendering
            assert await bus.publish(event_response,str(hr))

            # register tag.update feature
            #======================================
            async def update(actions):
                try:
                    await bus.publish(event_response+"_update",actions)
                except:
                    print("!!! concurrent write/read on redys !!!")
                return True

            hr.sendactions=update
            #======================================

            while RUNNING:
                params = await bus.get_event( event_interact )
                if params is not None:  # sometimes it's not a dict ?!? (bool ?!)
                    if params.get("cmd") == CMD_RENDER:
                        # just a false start, just need the current render
                        print(f">Process {pid} render {hid}")
                        assert await bus.publish(event_response,str(hr))
                    else:
                        print(f">Process {pid} interact {hid}:")
                        #-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\- UT
                        if params["oid"]=="ut": params["oid"]=id(hr.tag)
                        #-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-

                        actions = await hr.interact(**params)

                        assert await bus.publish(event_response+"_interact",actions)

                await asyncio.sleep(0.1)

            #consume all pending events
            assert await bus.unsubscribe( event_interact )

    asyncio.run( loop() )
    print(f">Process {pid} ended")

async def hrserver_orchestrator():
    with redys.v2.AClient() as bus:

        # prevent multi orchestrators
        if await bus.get("hrserver_orchestrator_running")==True:
            print("hrserver_orchestrator is already running")
            return
        else:
            print("hrserver_orchestrator started")
            await bus.set("hrserver_orchestrator_running",True)

        # register its main event
        await bus.subscribe( EVENT_SERVER )

        ps={}

        def killall(ps:dict):
            # try to send a EXIT CMD to all running ps
            for hid,infos in ps.items():
                ps[hid]["process"].kill()

        while 1:
            params = await bus.get_event( EVENT_SERVER )
            if params is not None:
                if params.get("cmd") == CMD_EXIT:
                    print(EVENT_SERVER, params.get("cmd") )
                    break
                elif params.get("cmd") == "CLEAN":
                    print(EVENT_SERVER, params.get("cmd") )
                    killall(ps)
                    continue
                elif params.get("cmd") == "PS":
                    print(EVENT_SERVER, params.get("cmd") )
                    from pprint import pprint
                    pprint(ps)
                    continue

                hid=params["hid"]
                key_init=str(params["init"])

                if hid in ps and ps[hid]["process"].is_alive():
                    # process is already running

                    if key_init == ps[hid]["key"]:
                        # it's the same initialization process

                        # so ask process to send back its render
                        assert await bus.publish(params["event_interact"],dict(cmd=CMD_RENDER))
                        continue
                    else:
                        # kill itself because it's not the same init params
                        print("Reload a new process",hid)
                        ps[hid]["process"].kill()

                        # and recreate another one later

                # create the process
                p=multiprocessing.Process(target=process, args=[],kwargs=params)
                p.start()

                # and save it in pool ps
                ps[hid]=dict( process=p, key=key_init, event_interact=params["event_interact"])

            await asyncio.sleep(0.1)

        assert await bus.unsubscribe( EVENT_SERVER )

        killall(ps)


    print("hrserver_orchestrator stopped")

async def wait_redys():
    bus=redys.v2.AClient()
    while 1:
        try:
            if await bus.ping()=="pong":
                break
        except:
            pass
        await asyncio.sleep(0.1)

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


async def hrserver():
    s=redys.v2.Server()
    s.start()

    await wait_redys()

    await hrserver_orchestrator()

    s.stop()




if __name__=="__main__":
    asyncio.run( hrserver() )
