# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import uuid,asyncio,time,sys
import redys
import redys.v2
from htagweb.server import EVENT_SERVER,Hid
import logging
logger = logging.getLogger(__name__)

TIMEOUT=2*60 # A interaction can take 2min max


class HrClient:
    def __init__(self,uid:str,fqn:str,js:str=None,sesprovidername=None):
        """ !!!!!!!!!!!!!!!!!!!! if js|sesprovidername is None : can't do a start() !!!!!!!!!!!!!!!!!!!!!!"""
        self.js=js
        self.bus = redys.v2.AClient()
        self.sesprovidername=sesprovidername

        self.hid=Hid.create(uid,fqn)

    def error(self, *a):
        txt=f".HrClient {self.hid.uid} {self.hid.fqn}: %s" % (" ".join([str(i) for i in a]))
        print(txt,flush=True,file=sys.stderr)
        logger.error(txt)


    async def _wait(self,event, s=TIMEOUT):
        # wait for a response
        t1=time.monotonic()
        while time.monotonic() - t1 < s:
            message = await self.bus.get_event( event )
            if message is not None:
                return message

        self.error(f"Event TIMEOUT ({s}s) on {event} !!!")
        return None

    async def start(self,*a,**k) -> str:
        """ Start the defined app with this params (a,k)
            (dialog with server event)
        """
        assert self.js, "You should define the js in HrPilot() !!!!!!"

        # subscribe for response
        await self.bus.subscribe( self.hid.event_response )

        # start the process app
        assert await self.bus.publish( EVENT_SERVER , dict(
            hid=self.hid,
            js=self.js,
            init= (a,k),
            sesprovidername=self.sesprovidername,
        ))

        # wait 1st rendering
        return await self._wait(self.hid.event_response) or "?!"


    async def interact(self,**params) -> dict:
        """ return htag'actions or None (if process doesn't answer, after timeout)
            (dialog with process event)
        """
        # subscribe for response
        await self.bus.subscribe( self.hid.event_interact_response )

        # post the interaction
        if await self.bus.publish( self.hid.event_interact, params ):
            # wait actions
            return await self._wait(self.hid.event_interact_response) or {}
        else:
            self.error(f"Can't publish {self.hid.event_interact} !!!")



async def main():
    uid ="u1"
    p=HrClient(uid,"obj:App","//")
    #~ html=await p.start()
    #~ print(html)

    #~ actions=await p.interact( oid="ut", method_name="doit", args=[], kargs={}, event={} )
    #~ print(actions)

    await p.kill()
    await p.kill()
    await p.kill()
    #~ await p.kill()
    #~ await p.kill()
    #~ await HrPilot.list()
    #~ await HrPilot.clean()

if __name__=="__main__":
    asyncio.run( main() )
