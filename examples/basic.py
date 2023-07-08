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
    Manager().ping( "hello" )
    DATA+=1
    return RedirectResponse("/")



def mainprocess(input,output):
    print("MAINPROCESS")

    async def ping(msg):
        return f"hello {msg}"

    methods=locals()

    async def loop():
        while 1:
            action,(a,k) = input.recv()
            print("::: RECV=",action,file=sys.stdout,flush=True)
            if action=="quit":
                break

            method=methods[action]
            # logger.info("Process %s: %s",uid,action)
            r=await method(*a,**k)

            output.send( r )

    asyncio.run( loop() )
    print("MAINPROCESS EXITED")


class Manager:
    _p=multiprocessing.Manager().dict()

    def __init__(self):
        if not Manager._p:
            qs,qr=multiprocessing.Pipe()
            rs,rr=multiprocessing.Pipe()
            Manager._p["input"]=qs
            Manager._p["output"]=rr

            ps = multiprocessing.Process(target=mainprocess, args=[qr,rs])
            ps.start()

        self.pp=Manager._p

    def shutdown(self):
        if self.pp:
            self.pp["input"].send( ("quit",([],{}) ))
            self.pp=None
            del Manager._p

    def __getattr__(self,action:str):
        def _(*a,**k):
            self.pp["input"].send( (action,(a,k)))

            x=self.pp["output"].recv()
            print(f"::manager action {action}({a}), recept={x}")
            return x
        return _


async def startup():
    c=Manager()     # only one will run !

    await asyncio.sleep(1)
    c.ping( "debut" )

async def shutdown():
    Manager().shutdown()

app = Starlette(debug=True, routes=[
    Route('/', homepage),
    Route('/inc', inc),
],on_startup=[startup],on_shutdown=[shutdown])

# import uvicorn
# uvicorn.run(app)