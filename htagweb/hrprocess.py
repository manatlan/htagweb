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
from asyncio import LimitOverrunError

from .session import Session
from .fifo import AsyncStream

import logging
logger = logging.getLogger(__name__)

async def main(f:AsyncStream,moduleapp:str,timeout_interaction,timeout_inactivity):
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
        # create the update socket on the first tag.update !
        try:
            if not os.path.exists(f.UPDATE_SOCKET):
                # For update socket, we'll use a simple approach with a temporary file
                # since we need one-way communication for updates
                pass

            # For now, keep the same logic but we'll improve this later
            # This is a placeholder for the update mechanism
            log("sendactions (update):",actions)
            return True
        except Exception as e:
            log("update socket error:",e)
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
        time_activity = time.monotonic()
        
        # Start the Unix socket server
        async def handle_client(reader, writer):
            """Handle incoming client connections"""
            nonlocal time_activity
            try:
                while sys.running:
                    # Read the command from the client
                    try:
                        data = await reader.readline()
                        if not data:
                            break
                    except asyncio.LimitOverrunError as e:
                        log(f"Message too large (limit: 10Mo) from client: {e}")
                        r["err"] = f"Message too large (limit: 10Mo): {e}"
                        writer.write((json.dumps(r) + '\n').encode())
                        await writer.drain()
                        break
                        
                    frame = data.decode().strip()
                    if frame:
                        time_activity = time.monotonic()
                        
                        # Process the command directly
                        q = json.loads(frame)
                        r = {}
                        try:
                            r["response"] = await cmd(**q)
                        except Exception as e:
                            if hasattr(sys, "hr") and sys.hr and sys.hr.fullerror:
                                err = traceback.format_exc()
                            else:
                                err = str(e)
                            r["err"] = err
                        
                        # Send the response back to the client
                        writer.write((json.dumps(r) + '\n').encode())
                        await writer.drain()
                        
                        if "err" in r:
                            raise Exception(r["err"])
            except Exception as e:
                log("Client handler error:", e)
            finally:
                writer.close()
                await writer.wait_closed()

        server = await asyncio.start_unix_server(
            handle_client,
            path=f.CLIENT_TO_SERVER_SOCKET,
            limit=10*1024*1024  # 10Mo pour gérer les très gros échanges de données
        )
        
        # Main loop to check for inactivity timeout
        while sys.running:
            if timeout_inactivity:
                # Check for inactivity timeout
                if time.monotonic() - time_activity > timeout_inactivity:
                    log(f"TIMEOUT inactivity ({timeout_inactivity}s), suicide !")
                    break
                await asyncio.sleep(1.0)
            else:
                # No timeout, just wait
                await asyncio.sleep(1.0)
        
        # Server context
        async with server:
            # Run the server in the background
            server_task = asyncio.create_task(server.serve_forever())
            
            # Main loop to check for inactivity timeout
            while sys.running:
                if timeout_inactivity:
                    # Check for inactivity timeout
                    if time.monotonic() - time_activity > timeout_inactivity:
                        log(f"TIMEOUT inactivity ({timeout_inactivity}s), suicide !")
                        sys.running = False
                        break
                    await asyncio.sleep(1.0)
                else:
                    # No timeout, just wait
                    await asyncio.sleep(1.0)
            
            # Cancel the server task
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        log("error (EXIT)", e)
    finally:
        f.removePipes()
        log("EXITED (no more sockets)")


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

        f=AsyncStream(uid,moduleapp) 
        f.createPipes()
        q.put("")

        try:
            asyncio.run( main(f,moduleapp, timeout_interaction,timeout_inactivity ) )
        except KeyboardInterrupt:
            print("\nServeur: Arrêté par l'utilisateur.")
    except Exception as e:
        q.put(str(e))
