from starlette.applications import Starlette
from starlette.responses import HTMLResponse,RedirectResponse
from starlette.routing import Route
import os

DATA=1

async def homepage(request):
    return HTMLResponse(f"<h3>{os.getpid()}</h3>{DATA} <a href='/inc'>inc</a>")

async def inc(request):
    global DATA
    DATA+=1
    return RedirectResponse("/")


app = Starlette(debug=True, routes=[
    Route('/', homepage),
    Route('/inc', inc),
])

# import uvicorn
# uvicorn.run(app)