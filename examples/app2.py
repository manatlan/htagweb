from htag import Tag # the only thing you'll need ;-)
import os

class App(Tag.body):
    def init(self):
        self.call.redraw()
        self.nb=0

    def clir(self,o):
        self.state.clear()
        self.redraw()

    def redraw(self):
        self.clear()
        self+= Tag.div(os.getpid())
        self <= Tag.button("add", _onclick=self.sett)
        self <= Tag.button("clir", _onclick=self.clir)
        self+=self.state.get("toto","?")
        self <= Tag.hr() + Tag.button("add", _onclick=self.addd) + Tag.span(self.nb)
        self <= Tag.hr() + Tag.button("exit", _onclick=self.bye)

    def sett(self,o):
        self.state["toto"]=self.state.get("toto",0) + 1
        self.redraw()

    def addd(self,o):
        self.nb+=1
        self.redraw()

    def bye(self,o):
        self.set("bye")
        self.exit()
