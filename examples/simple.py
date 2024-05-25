
# -*- coding: utf-8 -*-

# a classic app, which is runned here with htag.Runner !
# btw this app is used in a htagweb context, thru pytest

from htag import Tag
import asyncio,time

class App(Tag.body):
    statics="body {background:#EEE;}"

    def init(self):
        self.place = Tag.div()
        asyncio.ensure_future( self.loop_timer() )
        self <= "Hello World"
        self <= self.place
        self <= Tag.button("exit", _onclick=lambda ev: self.exit())
        self <= Tag.button("Say hi", _onclick=self.sayhi)

    async def sayhi(self,ev):
        self <= "hi!"

    async def loop_timer(self):
        while 1:
            await asyncio.sleep(0.5)
            self.place.clear(time.time() )
            if not await self.place.update(): # update component using current websocket
                # break if can't (<- good practice to kill this asyncio/loop)
                break

#=================================================================================
from htag.runners import Runner

if __name__ == "__main__":

    # import logging
    # logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.INFO)
    # logging.getLogger("htag.tag").setLevel( logging.INFO )
    # logging.getLogger("htag.render").setLevel( logging.INFO )


    Runner(App).run()
