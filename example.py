from htag import Tag

from htag import Tag
import json

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
        self.orendu.set( json.dumps( dict(self.session), indent=1))

class App(Tag.body):
    imports=[TagSession]
    statics=b"window.error=alert"
    def init(self):
        # del self.session["apps.draw.App"]
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

        self <= Tag.button("inc integer",_onclick=inc_test_session)
        self <= Tag.button("add list",_onclick=addd)
        self <= Tag.button("clear",_onclick=clllll)
        self <= TagSession()




# With Web http runner provided by htag
#------------------------------------------------------
# from htag.runners import WebHTTP
# WebHTTP( App ).run()

# With htagweb.WebServer runner provided by htagweb
#------------------------------------------------------

if __name__=="__main__":
    from htagweb import AppServer,RedysServer
    app=RedysServer( "example:App" ,parano=False)
    app.run(openBrowser=True)
