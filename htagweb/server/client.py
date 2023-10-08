# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import multiprocessing
import uuid,asyncio,time,sys
import redys
import redys.v2
from htagweb.server import CMD_RESP_RECREATE, CMD_RESP_RENDER, CMD_PS_REUSE, KEYAPPS,Hid, hrprocess
import logging
logger = logging.getLogger(__name__)

TIMEOUT=2*60 # A interaction can take 2min max


def startProcess(params:dict):
    p=multiprocessing.Process(target=hrprocess, args=[],kwargs=params)
    p.start()
    return p


class HrClient:
    def __init__(self,uid:str,fqn:str,js:str=None,sesprovidername=None,http_only=False):
        """ !!!!!!!!!!!!!!!!!!!! if js|sesprovidername is None : can't do a start() !!!!!!!!!!!!!!!!!!!!!!"""
        self.js=js
        self.bus = redys.v2.AClient()
        self.sesprovidername=sesprovidername
        self.useUpdate = not http_only

        self.hid=Hid.create(uid,fqn)

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
        await self.bus.subscribe( self.hid.event_response )

        #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
        params=dict(
            hid=self.hid,
            js=self.js,
            init= (a,k),
            sesprovidername=self.sesprovidername,
            useUpdate = self.useUpdate,
        )

        running_hids:list=await self.bus.get(KEYAPPS) or []
        if str(self.hid) in running_hids:
            self.log("Try to reuse process",self.hid)
            can = await self.bus.publish(self.hid.event_interact,dict(cmd=CMD_PS_REUSE,params=params))
            if not can:
                self.log("Can't answer the interaction REUSE !!!!")
        else:
            p=startProcess(params)
            self.log("Start a new process",self.hid,"in",p.pid)
        #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\

        # wait for a response
        t1=time.monotonic()
        while time.monotonic() - t1 < TIMEOUT:
            message = await self.bus.get_event( self.hid.event_response )
            if message is not None:
                if message.get("cmd")==CMD_RESP_RECREATE:
                    # the current process ask hrclient to recreate a new process
                    p=startProcess(params)
                    self.log("Start a new process",self.hid,"in",p.pid)
                elif message.get("cmd")==CMD_RESP_RENDER:
                    # the process has giver a right answer ... return the rendering
                    return message.get("render")

        self.error(f"Event TIMEOUT ({TIMEOUT}s) on {self.hid.event_response} !!!")
        return "?!"



    async def interact(self,**params) -> dict:
        """ return htag'actions or None (if process doesn't answer, after timeout)
            (dialog with process event)
        """
        try:
            # subscribe for response
            await self.bus.subscribe( self.hid.event_interact_response )

            # post the interaction
            if await self.bus.publish( self.hid.event_interact, params ):
                # wait actions
                return await self._wait(self.hid.event_interact_response) or {}
            else:
                self.error(f"Can't publish {self.hid.event_interact} !!!")
        except Exception as e:
            self.error("***HrClient.interact error***",e)
            return {}

    async def _wait(self,event, s=TIMEOUT):
        # wait for a response
        t1=time.monotonic()
        while time.monotonic() - t1 < s:
            message = await self.bus.get_event( event )
            if message is not None:
                return message

        self.error(f"Event TIMEOUT ({s}s) on {event} !!!")
        return None
