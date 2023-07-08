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
    send("hllllll")
    DATA+=1
    return RedirectResponse("/")

p=multiprocessing.Manager().dict()

def send(msg):
    qs,rr=p[1]
    qs.send(msg)

    x=rr.recv()
    print(f"COM SEND {msg}, recept={x}")


def mainprocess(input,output):
    print("MAINPROCESS")

    async def loop():
        while 1:
            event = input.recv()
            print("::: RECV=",event,file=sys.stdout,flush=True)
            if event=="quit":
                break
            output.send(f"hello {event}")

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
        qs,qr=multiprocessing.Pipe()
        rs,rr=multiprocessing.Pipe()
        p[1]=qs,rr

        ps = multiprocessing.Process(target=mainprocess, args=[qr,rs])
        ps.start()

        await asyncio.sleep(1)
        send( "debut" )

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