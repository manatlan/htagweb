from htag import Tag
import os

class App(Tag.body):
    statics="body {background:#EEE;}"

    def init(self,toto=""):
        self+= Tag.div(os.getpid())
        self += "Hello World toto="+toto
        self += "Hello World toto="+toto
        self += Tag.button("++",_onclick=self.bind.do())

    def do(self):
        self+= "h"
