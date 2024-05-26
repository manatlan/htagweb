import os
from examples import app1
from examples import app2

from htagweb import Runner
from starlette.responses import HTMLResponse

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
        <li><a href="/a1">a1</a> :   fqn=app1.App
        <li><a href="/a12">a12</a> : fqn=app1:App
        <li><a href="/a2">a2</a> :   fqn=app2.App (with session)
        <li><a href="/a22">a22</a> : fqn=app2 (with session)
        <li><a href="/k1">k1</a> : App with bug in init
        <li><a href="/k2">k2</a> : unknown app/fqn
        """
        return HTMLResponse(h)
    elif p=="a1":
        return await app.serve(request, "examples.app1.App")
    elif p=="a12":
        return await app.serve(request, "examples.app1:App")
    elif p=="a2":
        return await app.serve(request, app2.App )
    elif p=="a22":
        return await app.serve(request, app2 )
    elif p=="k1":
        return await app.serve(request, AppKo )
    elif p=="k2":
        return await app.serve(request, "nimp_module:nimp_name" )
    else:
        return HTMLResponse("404",404)

#/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
# **IMPORTANT** current host serving on SSL
# on your localmachine, switch ssl to False !!!
#/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
app=Runner(debug=True,ssl=True) 
app.add_route("/{path:path}", handlePath )

if __name__=="__main__":
    import logging
    logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.DEBUG)

    app.run(openBrowser=True)
