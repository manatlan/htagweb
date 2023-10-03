# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import uuid,asyncio,time
import redys
import redys.v2
from htagweb.server import EVENT_SERVER

TIMEOUT=20 # sec to wait answer from redys server #TODO: set better

class HrClient:
    def __init__(self,uid:str,fqn:str,js:str=None,sesprovidername=None):
        """ !!!!!!!!!!!!!!!!!!!! if js|sesprovidername is None : can't do a start() !!!!!!!!!!!!!!!!!!!!!!"""
        self.uid=uid
        self.fqn=fqn
        self.js=js
        self.bus = redys.v2.AClient()
        self.sesprovidername=sesprovidername

        self.hid=f"{uid}_{fqn}"
        self.event_response = f"response_{self.hid}"
        self.event_interact = f"interact_{self.hid}"

    async def _wait(self,event, s=TIMEOUT):
        # wait for a response
        t1=time.monotonic()
        while time.monotonic() - t1 < s:
            message = await self.bus.get_event( event )
            if message is not None:
                return message

        return None

    async def start(self,*a,**k) -> str:
        """ Start the defined app with this params (a,k)
            (dialog with server event)
        """
        assert self.js, "You should define the js in HrPilot() !!!!!!"

        # subscribe for response
        await self.bus.subscribe( self.event_response )

        # start the process app
        assert await self.bus.publish( EVENT_SERVER , dict(
            uid=self.uid,
            hid=self.hid,
            event_response=self.event_response,
            event_interact=self.event_interact,
            fqn=self.fqn,
            js=self.js,
            init= (a,k),
            sesprovidername=self.sesprovidername,
        ))

        # wait 1st rendering
        return await self._wait(self.event_response) or "?!"

    # async def kill(self):
    #     """ Kill the process
    #         (dialog with process event)
    #     """
    #     assert await self.bus.publish( self.event_interact, dict(cmd="EXIT") )


    async def interact(self,**params) -> dict:
        """ return htag'actions or None (if process doesn't answer, after timeout)
            (dialog with process event)
        """
        # subscribe for response
        await self.bus.subscribe( self.event_response+"_interact" )

        # post the interaction
        assert await self.bus.publish( self.event_interact, params )

        # wait actions
        return await self._wait(self.event_response+"_interact") or {}


    @staticmethod
    async def list():
        """ SERVER COMMAND
            (dialog with server event)
        """
        with redys.v2.AClient() as bus:
            assert await bus.publish( EVENT_SERVER, dict(cmd="PS") )

    @staticmethod
    async def clean():
        """ SERVER COMMAND
            (dialog with server event)
        """
        with redys.v2.AClient() as bus:
            assert await bus.publish( EVENT_SERVER, dict(cmd="CLEAN") )


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
