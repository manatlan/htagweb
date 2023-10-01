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
            print(e)
            pass
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



def process(hid,event_response,event_interact,fqn,js,init,sesprovidername):
    if sesprovidername is None:
        sesprovidername="createFile"
    import htagweb.sessions
    createSession=getattr(htagweb.sessions,sesprovidername)

    uid=hid.split("_")[0]

    pid = os.getpid()
    async def loop():
        if os.getcwd() not in sys.path: sys.path.insert(0,os.getcwd())
        klass=importClassFromFqn(fqn)

        RUNNING=True
        def exit():
            RUNNING=False

        session = await createSession(uid)

        styles=Tag.style("body.htagoff * {cursor:not-allowed !important;}")

        hr=HRenderer( klass ,js, init=init, exit_callback=exit, fullerror=True, statics=[styles,],session = session)

        print(f">Process {pid} started with :",hid,init)

        with redys.v2.AClient() as bus:
            # publish the 1st rendering
            assert await bus.publish(event_response,str(hr))

            # register tag.update feature
            #======================================
            # async def update(actions):
            #     try:
            #         await bus.publish(event_response+"_update",actions)
            #     except:
            #         print("!!! concurrent write/read on redys !!!")
            #     return True

            # hr.sendactions=update
            #======================================


            # subscribe for interaction
            await bus.subscribe( event_interact )

            while RUNNING:
                params = await bus.get_event( event_interact )
                # try: #TODO: but fail the test_server.py ?!?!?
                # except: # some times it crash ;-(
                #     print("!!! concurrent sockets reads !!!")
                #     params = None
                if params and isinstance(params,dict):  # sometimes it's not a dict ?!? (bool ?!)
                    if params.get("cmd") == CMD_EXIT:
                        print(f">Process {pid} {hid} killed")
                        break
                    elif params.get("cmd") == CMD_RENDER:
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

            # unsubscribe for interaction
            await bus.unsubscribe( event_interact )

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

        async def killall(ps:dict):
            # try to send a EXIT CMD to all running ps
            for hid,infos in ps.items():
                assert await bus.publish(infos["event_interact"],dict(cmd=CMD_EXIT))

        while 1:
            params = await bus.get_event( EVENT_SERVER )
            if params:
                if params.get("cmd") == CMD_EXIT:
                    print(EVENT_SERVER, params.get("cmd") )
                    break
                elif params.get("cmd") == "CLEAN":
                    print(EVENT_SERVER, params.get("cmd") )
                    await killall(ps)
                    continue
                elif params.get("cmd") == "PS":
                    print(EVENT_SERVER, params.get("cmd") )
                    from pprint import pprint
                    pprint(ps)
                    continue

                hid=params["hid"]
                key_init=str(params["init"])

                if hid in ps:
                    # process is already running

                    if key_init == ps[hid]["key"]:
                        # it's the same initialization process

                        # so ask process to send back its render
                        # (TODO:sometimes it's not possible to assert it)
                        await bus.publish(params["event_interact"],dict(cmd=CMD_RENDER))
                        continue
                    else:
                        # kill itself because it's not the same init params
                        # (TODO:sometimes it's not possible to assert it)
                        await bus.publish(params["event_interact"],dict(cmd=CMD_EXIT))
                        # and recreate another one later

                # create the process
                p=multiprocessing.Process(target=process, args=[],kwargs=params)
                p.start()

                # and save it in pool ps
                ps[hid]=dict( process=p, key=key_init, event_interact=params["event_interact"])

            await asyncio.sleep(0.1)

        await bus.unsubscribe( EVENT_SERVER )

        await killall(ps)


    print("hrserver_orchestrator stopped")



async def hrserver():
    print("HRSERVER started")

    async def delay():
        await asyncio.sleep(0.3)
        await hrserver_orchestrator()

    asyncio.ensure_future( delay() )
    await redys.Server()


async def hrserver2():
    print("HRSERVER2 started")

    async def delay():
        await asyncio.sleep(0.3)
        await hrserver_orchestrator()

    asyncio.ensure_future( delay() )

    s=redys.v2.Server()
    s.start()
    while 1:
        await asyncio.sleep(1)

if __name__=="__main__":
    asyncio.run( hrserver2() )
