# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import uuid,asyncio
import redys,time
from htagweb.server import EVENT_SERVER

TIMEOUT=30 # sec to wait answer from redys server

class HrPilot:
    def __init__(self,uid:str,fqn:str,js:str=None):
        """ !!!!!!!!!!!!!!!!!!!! if js is None : can't do a start() !!!!!!!!!!!!!!!!!!!!!!"""
        self.fqn=fqn
        self.js=js
        self.bus = redys.AClient()

        self.hid=f"{uid}_{fqn}"
        self.event_response = f"response_{self.hid}"
        self.event_interact = f"interact_{self.hid}"

    async def _wait(self,s=TIMEOUT):
        # wait for a response
        t1=time.monotonic()
        while time.monotonic() - t1 < s:
            message = await self.bus.get_event( self.event_response )
            if message:
                return message

            await asyncio.sleep(0.1)

        return None

    async def start(self,*a,**k) -> str:
        """ Start the defined app with this params (a,k)
            (dialog with server event)
        """
        assert self.js, "You should define the js in HrPilot() !!!!!!"

        # subscribe for response
        await self.bus.subscribe( self.event_response )

        # start the process app
        await self.bus.publish( EVENT_SERVER , dict(
            hid=self.hid,
            event_response=self.event_response,
            event_interact=self.event_interact,
            fqn=self.fqn,
            js=self.js,
            init= (a,k),
        ))

        # wait 1st rendering
        html = await self._wait()

        return html

    async def kill(self):
        """ Kill the process
            (dialog with process event)
        """
        await self.bus.publish( self.event_interact, dict(cmd="EXIT") )


    async def interact(self,**params) -> dict:
        """ return htag'actions or None (if process doesn't answer, after timeout)
            (dialog with process event)
        """
        # subscribe for response
        await self.bus.subscribe( self.event_response )

        # post the interaction
        await self.bus.publish( self.event_interact, params )

        # wait actions
        return await self._wait()


    @staticmethod
    async def list():
        """ SERVER COMMAND
            (dialog with server event)
        """
        with redys.AClient() as bus:
            await bus.publish( EVENT_SERVER, dict(cmd="PS") )
    #~ @staticmethod
    #~ async def stop():
        #~ with redys.AClient() as bus:
            #~ await bus.publish( EVENT_SERVER, dict(cmd="EXIT") )
    @staticmethod
    async def clean():
        """ SERVER COMMAND
            (dialog with server event)
        """
        with redys.AClient() as bus:
            await bus.publish( EVENT_SERVER, dict(cmd="CLEAN") )


async def main():
    uid ="u1"
    p=HrPilot(uid,"obj:App","//")
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
