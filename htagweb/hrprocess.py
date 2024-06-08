# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2024 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import sys
import signal
import os
import time
import json
import asyncio
import importlib
import inspect
import traceback
from htag import Tag
from htag.render import HRenderer
import aiofiles

from .session import Session
from .fifo import Fifo

import logging
logger = logging.getLogger(__name__)

async def main(f:Fifo,moduleapp:str,timeout_interaction,timeout_inactivity):
    print("Serveur:",f)

    with open(f.PID_FILE,"w+") as fid:
        fid.write(str(os.getpid()))

    ses=Session(f.uid)

    sys.hr=None             # save as global, in sys module (bad practice !!! but got sense)
    sys.running=True
    def process_exit():
        sys.running=False

    def log(*a):
        msg = " ".join([str(i) for i in ["hrprocess",f,":"] + list(a)])
        # logging.warning( msg )
        print(msg,flush=True,file=sys.stderr)

    async def sendactions(actions:dict) -> bool:
        # create the fifo on the first tag.update !
        try:
            if not os.path.exists(f.UPDATE_FIFO):
                os.mkfifo(f.UPDATE_FIFO)
                os.chmod(f.UPDATE_FIFO, 0o700)


            async with aiofiles.open(f.UPDATE_FIFO, mode='w') as fifo_update:
                log("sendactions (update):",actions)
                await fifo_update.write(json.dumps(actions) + '\n')
                await fifo_update.flush()
            return True
        except Exception as e:
            log("update fifo error:",e)
            return False

    async def sendactions_close(actions:dict) -> bool:
        return False

    async def cmd(cmd,**args) -> str:
        if cmd=="create":
            ia,ik = tuple(args["init"] or ([],{}))
            init=(tuple(ia),dict(ik))
            
            if sys.hr:
                def destroy():
                    sys.hr.sendactions = sendactions_close
                    del sys.hr.tag
                    del sys.hr
                    sys.hr=None

                if sys.hr.init != init:
                    log("recreate, because params change")
                    destroy()
                elif sys.hr.timestamp != os.path.getmtime(sys.hr.klassfile):
                    log("recreate, because filedate change")
                    destroy()


            if sys.hr is None:
                klass=moduleapp2class(moduleapp)
                sys.hr=HRenderer(
                    klass,
                    js=args["js"],
                    init=init,
                    fullerror=args["fullerror"],
                    exit_callback=process_exit,
                    session=ses,
                )
                sys.hr.klassfile = inspect.getfile(klass)
                sys.hr.timestamp=os.path.getmtime(sys.hr.klassfile)
                sys.hr.sendactions = sendactions
                log("create HRenderer")
            else:
                log("reuse previous HRenderer")

            return str(sys.hr)
        elif cmd=="interact":
            log("interact with",args['id'],args['method'])
            coro=sys.hr.interact(args['id'],args['method'],args["args"],args["kargs"],args["event"])
            try:
                actions= await asyncio.wait_for(coro, timeout=timeout_interaction) 
                #=======================================
                # always save session after interaction # (when using FileDict & co)
                # not needed for shm
                # sys.hr.session._save()     
                #=======================================
            except asyncio.TimeoutError:
                log("timeout interaction > kill")
                process_exit()
                actions={}

            return actions
        elif cmd=="exit":
            log("exit itself")
            process_exit()
            return "exiting"
        else:
            return f"unknown '{cmd}' ?!"

    try:
        time_activity=time.monotonic()

        async with aiofiles.open(f.CLIENT_TO_SERVER_FIFO, mode='r') as fifo_in, aiofiles.open(f.SERVER_TO_CLIENT_FIFO, mode='w') as fifo_out:
            while sys.running:
                # Lire la commande depuis le pipe
                frame = await fifo_in.readline()
                if frame.strip():
                    time_activity=time.monotonic()

                    # log("recept command:",frame)
                    q=json.loads(frame.strip())
                    r={}
                    try:
                        r["response"]=await cmd(**q)
                    except Exception as e:
                        # HRenderer.interact has its own system, but needed for create ;-(
                        if hasattr( sys, "hr") and sys.hr and sys.hr.fullerror:
                            err=traceback.format_exc()
                        else:
                            err=str(e)
                        r["err"]=err
                        
                    # Envoyer la réponse au client
                    await fifo_out.write(json.dumps(r) + '\n')
                    await fifo_out.flush()
                
                    if "err" in r:
                        raise Exception(r["err"])

                if timeout_inactivity: # if timeout_inactivity is set
                    if time.monotonic() - time_activity > timeout_inactivity:
                        # it suicides after the timeout
                        log(f"TIMEOUT inactivity ({timeout_inactivity}s), suicide !")
                        break

    except Exception as e:
        log("error (EXIT)",e)
    finally:
        f.removePipes()
        log("EXITED (no more pipes)")


def moduleapp2class(moduleapp:str):
    assert "." in moduleapp, f"miss '.' in moduleapp '{moduleapp}'"
    *module,app = moduleapp.split(".")
    module=importlib.import_module(".".join(module))
    importlib.reload(module)

    klass= getattr(module,app)
    if not ( inspect.isclass(klass) and issubclass(klass,Tag) ):
        raise Exception(f"'{moduleapp}' is not a htag.Tag subclass")
    return klass

def normalize(fqn):
    if ":" not in fqn:
        # replace last "." by ":"
        fqn="".join( reversed("".join(reversed(fqn)).replace(".",":",1)))
    return fqn

def classname(klass:Tag) -> str:
    return klass.__module__+":"+klass.__qualname__


def process(q, uid:str,moduleapp:str,timeout_interaction:int,timeout_inactivity:int):
    try:
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)    
        
        # test that in will workd further
        klass=moduleapp2class(moduleapp)

        f=Fifo(uid,moduleapp) 
        f.createPipes()
        q.put("")

        try:
            asyncio.run( main(f,moduleapp, timeout_interaction,timeout_inactivity ) )
        except KeyboardInterrupt:
            print("\nServeur: Arrêté par l'utilisateur.")
    except Exception as e:
        q.put(str(e))
