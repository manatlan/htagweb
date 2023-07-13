from htag import Tag
import os,asyncio

class App(Tag.body):
    statics="body {background:#EEE;}"

    def init(self,toto=""):
        self+= Tag.div(os.getpid())
        self += "query_params 'toto'="+toto
        self += Tag.button("+h",_onclick=self.bind.do())
        self += Tag.button("yield 123",_onclick=self.bind.doy())

    def do(self):
        self+= "h"

    async def doy(self):
        for i in "123":
            self+= i
            await asyncio.sleep(0.2)
            yield
