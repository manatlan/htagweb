from htag import Tag

class App(Tag.div):
    def init(self):
        self+= "hello world"

# With Web http runner provided by htag
#------------------------------------------------------
# from htag.runners import WebHTTP
# WebHTTP( App ).run()

# With htagweb.WebServer runner provided by htagweb
#------------------------------------------------------
from htagweb import WebServer # or WebServerWS
WebServer( App ).run(openBrowser=True)
