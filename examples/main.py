import os,sys; sys.path.insert(0,"..")
from htagweb import WebServer,WebServerWS
from starlette.responses import HTMLResponse

import app1
import app2

#=-
from htag import Tag
class AppKo(Tag.div):
    def init(self):
        self+= 42/0
#=-

async def handlePath(request):
    app=request.app
    p=request.path_params.get("path")
    if p == "":
        h=f"""
        {os.getpid()}
        <li><a href="/a1">a1</a> : app without session
        <li><a href="/a12">a12</a> : app without session
        <li><a href="/a2">a2</a> : app with session (not renewed)
        <li><a href="/a22">a22</a> : app with session (renewed at each refresh)
        <li><a href="/k1">k1</a> : App with bug in init
        <li><a href="/k2">k2</a> : unknown app/fqn
        """
        return HTMLResponse(h)
    elif p=="a1":
        return await app.serve(request, "app1.App")
    elif p=="a12":
        return await app.serve(request, "app1:App")
    elif p=="a2":
        return await app.serve(request, app2.App )
    elif p=="a22":
        return await app.serve(request, app2, renew=True )
    elif p=="k1":
        return await app.serve(request, AppKo )
    elif p=="k2":
        return await app.serve(request, "nimp_module.nimp_name" )
    else:
        return HTMLResponse("404",404)


app=WebServer()
app.add_route("/{path:path}", handlePath )

if __name__=="__main__":
    import logging
    logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.DEBUG)

    app.run(openBrowser=True)
