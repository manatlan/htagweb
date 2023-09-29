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
import os,sys,importlib,inspect
from htag import Tag


from multiprocessing import Process
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


def process(hid,event_response,event_interact,fqn,js,init):
    pid = os.getpid()
    async def loop():
        if os.getcwd() not in sys.path: sys.path.insert(0,os.getcwd())
        klass=importClassFromFqn(fqn)

        RUNNING=True
        def exit():
            RUNNING=False

        session={}
        styles=Tag.style("body.htagoff * {cursor:not-allowed !important;}")

        hr=HRenderer( klass ,js, init=init, exit_callback=exit, fullerror=True, statics=[styles,],session = session)

        # register the hr.sendactions, for tag.update feature
        #TODO: implement tag.update !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #TODO: implement tag.update !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #TODO: implement tag.update !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #hr.sendactions=lambda actions: self._sendback(websocket,json.dumps(actions))
        #TODO: implement tag.update !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #TODO: implement tag.update !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #TODO: implement tag.update !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


        print(f"Process {pid} started with :",hid,init,event_response,event_interact)

        with redys.AClient() as bus:
            # publish the 1st rendering
            await bus.publish(event_response,str(hr))

            # subscribe for interaction
            await bus.subscribe( event_interact )

            while RUNNING:
                params = await bus.get_event( event_interact )
                if params:
                    if params.get("cmd") == CMD_EXIT:
                        print(f"Process {pid} {hid} killed")
                        break
                    elif params.get("cmd") == CMD_RENDER:
                        # just a false start, just need the current render
                        print(f"Process {pid} just a render of {hid}")
                        await bus.publish(event_response,str(hr))
                    else:
                        print(f"Process {pid} interact {hid}:",params)
                        #-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\- UT
                        if params["oid"]=="ut": params["oid"]=id(hr.tag)
                        #-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-

                        actions = await hr.interact(**params)
                        await bus.publish(event_response,actions)

                await asyncio.sleep(0.1)

            # prevent the server that this process is going dead
            await bus.publish( EVENT_SERVER, dict(cmd="REMOVE",hid=hid) )

            # unsubscribe for interaction
            await bus.unsubscribe( event_interact )

    asyncio.run( loop() )
    print(f"Process {pid} ended")

async def starters():
    print("htag starters started")
    with redys.AClient() as bus:
        await bus.subscribe( EVENT_SERVER )

        ps={}

        async def killall(ps:dict):
            # try to send a EXIT CMD to all running ps
            for hid,infos in ps.items():
                await bus.publish(infos["event_interact"],dict(cmd=CMD_EXIT))

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
                elif params.get("cmd") == "REMOVE":
                    hid=params.get("hid")
                    print(EVENT_SERVER, params.get("cmd"),hid )
                    del ps[hid] # remove from pool
                    continue

                hid=params["hid"]
                key_init=str(params["init"])

                if hid in ps:
                    # process is already running

                    if key_init == ps[hid]["key"]:
                        # it's the same initialization process

                        # so ask process to send back its render
                        await bus.publish(params["event_interact"],dict(cmd=CMD_RENDER))
                        continue
                    else:
                        # kill itself because it's not the same init params
                        await bus.publish(params["event_interact"],dict(cmd=CMD_EXIT))
                        # and recreate another one later

                # create the process
                p=Process(target=process, args=[],kwargs=params)
                p.start()

                # and save it in pool ps
                ps[hid]=dict( process=p, key=key_init, event_interact=params["event_interact"])

            await asyncio.sleep(0.1)

        await bus.unsubscribe( EVENT_SERVER )

        await killall(ps)


    print("htag starters stopped")

async def hrserver():
    print("HRSERVER started")

    async def delay():
        await asyncio.sleep(2)
        print("go")
        await starters()

    asyncio.ensure_future( delay() )
    await redys.Server()
    # asyncio.ensure_future( redys.Server() )
    # await starters()


if __name__=="__main__":
    asyncio.run( hrserver() )
