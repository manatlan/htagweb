import os,sys; sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from htagweb.manager import Manager

from audioop import mul
from starlette.applications import Starlette
from starlette.responses import HTMLResponse,RedirectResponse
from starlette.routing import Route
import os,multiprocessing
import sys,asyncio
# gunicorn -w 4 -k uvicorn.workers.UvicornH11Worker -b localhost:8000 --preload basic:app

DATA=1

MANAGER:Manager = None

async def homepage(request):
    return HTMLResponse(f"<h3>{os.getpid()}</h3>{DATA} <a href='/inc'>inc</a>")

async def inc(request):
    global DATA
    MANAGER.ping( "hello" )
    DATA+=1
    return RedirectResponse("/")


async def startup():
    global MANAGER
    MANAGER=Manager()     # only one will run !

    await asyncio.sleep(1)
    MANAGER.ping( "debut" )

async def shutdown():
    MANAGER.shutdown()

app = Starlette(debug=True, routes=[
    Route('/', homepage),
    Route('/inc', inc),
],on_startup=[startup],on_shutdown=[shutdown])

# import uvicorn
# uvicorn.run(app)