import os,sys; sys.path.insert(0,r"..")

"""
this is not a htagweb example !!!!
this is not a htagweb example !!!!
this is not a htagweb example !!!!
this is not a htagweb example !!!!
this is not a htagweb example !!!!

this is for my own tests ;-)
"""

import contextlib,json

from starlette.applications import Starlette
from starlette.responses import HTMLResponse,RedirectResponse
from starlette.routing import Route
import os,multiprocessing,threading
import sys,asyncio,pickle
# gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b localhost:8000 --preload basic:app
import logging

logger = logging.getLogger(__name__)

from htagweb.manager import Manager
#############################################################################
#############################################################################
#############################################################################
#############################################################################


async def homepage(request):
    async with request.app.state.manager.session( "u1" ) as d:
        if "x" not in d:
            d["x"]=0
        return HTMLResponse(f"<h3>{os.getpid()} </h3>{d['x']} <a href='/inc'>inc</a>")

async def inc(request):
    async with request.app.state.manager.session( "u1" ) as d:
        d["x"]=d["x"]+1

    #~ x=await request.app.state.manager.ht_create("u1","test_hr.App","//")
    #~ print(x)

    return RedirectResponse("/")



@contextlib.asynccontextmanager
async def htagweb_life(app):
    app.state.manager = Manager()
    try:
        # tente un ping
        #~ x=await app.state.manager.ping()
        #~ print("recept",x)
        print("WORKER",os.getpid(),"started")
        yield
        print("WORKER",os.getpid(), "stopped")

    finally:
        await app.state.manager.stop()

app = Starlette(debug=True, routes=[Route('/', homepage),Route('/inc', inc)],lifespan=htagweb_life)

# import uvicorn
# uvicorn.run(app)
