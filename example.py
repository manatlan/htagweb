from htag import Tag
import json,asyncio,time

"""
Complex htag's app to test:

    - a dynamic object (TagSession), which got a render method (new way)
    - using tag.state (in session)
    - using tag.update with a task in a loop
    - can recreate itself (when init params change)

"""

class TagSession(Tag.div):  #dynamic component (compliant htag >= 0.30) !!!! FIRST IN THE WORLD !!!!
    def init(self):
        self["style"]="border:1px solid black"
        self.otitle = Tag.h3(_style="padding:0px;margin:0px;float:right")
        self.orendu = Tag.pre(_style="padding:0px;margin:0px")

        # draw ui
        self+=self.otitle
        self+=self.orendu

    def render(self):
        self.otitle.set( "Live Session" )
        self.orendu.set( json.dumps( dict(self.session.items()), indent=1))

class App(Tag.body):
    imports=[TagSession]
    statics=b"window.error=alert"
    def init(self,v="0"):
        self.place = Tag.div(js="console.log('I update myself')")
        asyncio.ensure_future( self.loop_timer() )

        def inc_test_session(o):
            v=int(self.state.get("integer","0"))
            v=v+1
            self.state["integer"]=v
        def addd(o):
            if "list" in self.state:
                self.state["list"].append("x")    # <= this workd because tag.state.save() called in interaction (before guess rendering)
            else:
                self.state["list"]=[]
        def clllll(o):
            self.state.clear()


        self <= Tag.div(v)
        self <= Tag.button("inc integer",_onclick=inc_test_session)
        self <= Tag.button("add list",_onclick=addd)
        self <= Tag.button("clear",_onclick=clllll)
        #~ self <= Tag.button("yield",_onclick=self.yielder)
        self <= TagSession()

        self+=Tag.li(Tag.a("t0",_href="/"))
        self+=Tag.li(Tag.a("t1",_href="/?v=1"))
        self+=Tag.li(Tag.a("t2",_href="/?v=2"))
        self+=self.place

    #~ async def yielder(self,o):
        #~ for i in "ABCDEF":
            #~ await asyncio.sleep(0.3)
            #~ self+=i

    async def loop_timer(self):
        while 1:
            await asyncio.sleep(0.5)
            self.place.set(time.time() )
            if not await self.place.update(): # update component using current websocket
                # break if can't (<- good practice to kill this asyncio/loop)
                break


# With Web http runner provided by htag
#------------------------------------------------------
# from htag.runners import WebHTTP
# WebHTTP( App ).run()

# With htagweb.WebServer runner provided by htagweb
#------------------------------------------------------
from htagweb import SimpleServer,AppServer
app=AppServer( "example:App" ,parano=True)

if __name__=="__main__":
    app.run(openBrowser=True)
