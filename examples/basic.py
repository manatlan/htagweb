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
    Manager.send("ping","hllllll")
    DATA+=1
    return RedirectResponse("/")

p=multiprocessing.Manager().dict()

class Manager:
    @staticmethod
    def start():

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

        if not p:
            qs,qr=multiprocessing.Pipe()
            rs,rr=multiprocessing.Pipe()
            p["input"]=qs
            p["output"]=rr

            ps = multiprocessing.Process(target=mainprocess, args=[qr,rs])
            ps.start()
            return ps
        else:
            return None

    @staticmethod
    def quit():
        p["input"].send( ("quit",([],{}) ))

    @staticmethod
    def send(method,*a,**k):
        p["input"].send( (method,(a,k)))

        x=p["output"].recv()
        print(f"::manager action {method}({a}), recept={x}")
        return x

    # @classmethod
    # def __getattr__(cls,action:str):
    #     async def _(*a,**k):
    #         p["input"].send( (action,(a,k)))

    #         x=p["output"].recv()
    #         return x
    #     return _

ps=None

async def startup():
    global ps
    ps=Manager.start()

    await asyncio.sleep(1)
    Manager.send( "ping","debut" )

async def shutdown():
    global ps
    if ps: # the one who have started it, kill it ;-)
        Manager.quit()

app = Starlette(debug=True, routes=[
    Route('/', homepage),
    Route('/inc', inc),
],on_startup=[startup],on_shutdown=[shutdown])

# import uvicorn
# uvicorn.run(app)