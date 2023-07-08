from audioop import mul
from starlette.applications import Starlette
from starlette.responses import HTMLResponse,RedirectResponse
from starlette.routing import Route
import os,multiprocessing
import sys,asyncio
# gunicorn -w 4 -k uvicorn.workers.UvicornH11Worker -b localhost:8000 --preload basic:app

DATA=1

async def homepage(request):
    return HTMLResponse(f"<h3>{os.getpid()}</h3>{DATA} <a href='/inc'>inc</a>")

async def inc(request):
    global DATA
    qs,qr=p[1]
    qs.send("hello")
    print("COM SEND")
    DATA+=1
    return RedirectResponse("/")

p=multiprocessing.Manager().dict()

def mainprocess(qs,qr):
    print("MAINPROCESS")
    print(qs,qr,file=sys.stderr,flush=True)

    async def loop():
        while 1:
            event = qr.recv()
            print("::: RECV=",event,file=sys.stdout,flush=True)
            if event=="quit":
                break
            # qs.send(f"hello {event}")

    asyncio.run( loop() )
    print("MAINPROCESS EXITED")

ps=None

async def startup():
    global ps
    if p:
        ps=None
        print("already running")
    else:
        print("start")
        p[1]=multiprocessing.Pipe()

        ps = multiprocessing.Process(target=mainprocess, args=p[1])
        ps.start()

        await asyncio.sleep(1)
        qs,qr=p[1]
        qs.send( ("hello",42) )

async def shutdown():
    print("SHHHHHHHHHHHHHHHHHHHHHHUUUUUUUUUUUUUUUUUUUUUUTTTTTTTTTTTTTTTTTT",ps)
    if ps:
        print(">>>> it's me which has runned the mainprocess")
        qin,qout=p[1]
        qin.send("quit")
    else:
        print(">>>> it's NOT me which has runned the mainprocess !!!!!!!!!!!!!!")

app = Starlette(debug=True, routes=[
    Route('/', homepage),
    Route('/inc', inc),
],on_startup=[startup],on_shutdown=[shutdown])

# import uvicorn
# uvicorn.run(app)