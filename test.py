from htag import Tag

class App(Tag.div):
    def init(self):
        self+= "hello world"

from htagweb import WebServer # or WebServerWS
WebServer( App ).run(openBrowser=False)