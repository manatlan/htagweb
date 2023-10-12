# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import multiprocessing
import asyncio,time,sys
import json
from htagweb.server import CMD_RESP_RECREATE, CMD_RESP_RENDER, CMD_PS_REUSE, KEYAPPS,Hid, hrprocess, ServerClient
import logging
logger = logging.getLogger(__name__)


def startProcess(params:dict):
    p=multiprocessing.Process(target=hrprocess, args=[],kwargs=params)
    p.start()
    return p


class HrClient(ServerClient):
    def __init__(self,uid:str,
                 fqn:str,
                 js:str=None,
                 sesprovidername:str=None,
                 http_only:bool=False,
                 timeout_interaction:int=0,
                 timeout_inactivity:int=0
                 ):
        """ !!!!!!!!!!!!!!!!!!!! if js|sesprovidername is None : can't do a start() !!!!!!!!!!!!!!!!!!!!!!"""
        ServerClient.__init__(self)

        self.hid=Hid.create(uid,fqn)

        self.js=js
        self.sesprovidername=sesprovidername
        self.useUpdate = not http_only
        self.timeout_interaction = timeout_interaction or 60
        self.timeout_inactivity = timeout_inactivity

    def error(self, *a):
        txt=f".HrClient {self.hid.uid} {self.hid.fqn}: %s" % (" ".join([str(i) for i in a]))
        print(txt,flush=True,file=sys.stderr)
        logger.error(txt)

    def log(self, *a):
        txt=f".HrClient {self.hid.uid} {self.hid.fqn}: %s" % (" ".join([str(i) for i in a]))
        print(txt,flush=True,file=sys.stderr)
        logger.info(txt)


    async def start(self,*a,**k) -> str:
        """ Start the defined app with this params (a,k)
            (dialog with server event)
        """
        assert self.js, "You should define the js in HrPilot() !!!!!!"

        # subscribe for response
        await self._bus.subscribe( self.hid.EVENT_RESPONSE )

        #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
        params=dict(
            hid=self.hid,
            js=self.js,
            init= (a,k),
            sesprovidername=self.sesprovidername,
            useUpdate = self.useUpdate,
            timeout_inactivity = self.timeout_inactivity
        )

        running_hids:list=await self._bus.get(KEYAPPS) or []
        if str(self.hid) in running_hids:
            self.log("Try to reuse process",self.hid)
            can = await self._bus.publish(self.hid.EVENT_INTERACT,dict(cmd=CMD_PS_REUSE,params=params))
            if not can:
                self.log("Can't answer the interaction REUSE !!!!")
        else:
            p=startProcess(params)
            self.log("Start a new process",self.hid,"in",p.pid)
        #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\

        # wait for a response
        t1=time.monotonic()
        while time.monotonic() - t1 < self.timeout_interaction:
            message = await self._bus.get_event( self.hid.EVENT_RESPONSE )
            if message is not None:
                if message.get("cmd")==CMD_RESP_RECREATE:
                    # the current process ask hrclient to recreate a new process
                    p=startProcess(params)
                    self.log("Start a new process",self.hid,"in",p.pid)
                elif message.get("cmd")==CMD_RESP_RENDER:
                    # the process has giver a right answer ... return the rendering
                    return message.get("render")


        self.error(f"Event TIMEOUT ({self.timeout_interaction}s) on {self.hid.EVENT_RESPONSE} !!!")
        await self.kill(self.hid)
        return f"Timeout: App {self.hid.fqn} killed !"



    async def interact(self,**params) -> dict:
        """ return htag'actions or None (if process doesn't answer, after timeout)
            (dialog with process event)
        """
        try:
            # subscribe for response
            await self._bus.subscribe( self.hid.EVENT_INTERACT_RESPONSE )

            # post the interaction
            if await self._bus.publish( self.hid.EVENT_INTERACT, params ):
                # wait actions

                # wait for a response
                t1=time.monotonic()
                while time.monotonic() - t1 < self.timeout_interaction:
                    message = await self._bus.get_event( self.hid.EVENT_INTERACT_RESPONSE )
                    if message is not None:
                        return message

                self.error(f"Event TIMEOUT ({self.timeout_interaction}s) on {self.hid.EVENT_INTERACT_RESPONSE} !!!")
                await self.kill(self.hid)
                return dict(error=f"Timeout: App {self.hid.fqn} killed !")
            else:
                self.error(f"Can't publish {self.hid.EVENT_INTERACT} !!!")
        except Exception as e:
            self.error("***HrClient.interact error***",e)
            return {}

    async def loop_tag_update(self, hrsocket, websocket):
        event=self.hid.EVENT_RESPONSE_UPDATE

        #TODO: there is trouble here sometimes ... to fix !
        await self._bus.subscribe(event)

        try:
            while 1:
                actions = await self._bus.get_event( event )
                if actions is not None:
                    can = await hrsocket._sendback(websocket,json.dumps(actions))
                    if not can:
                        break
                await asyncio.sleep(0.1)
        except Exception as e:
            print("**loop_tag_update, broken bus, will stop the loop_tag_update !**")
        finally:
            await self._bus.unsubscribe(event)