# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2024 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

# gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b localhost:8000 --preload basic:app

#from shared_memory_dict import SharedMemoryDict

import contextlib
import asyncio
import os,sys
import sys
import json
import uuid
import logging
import uvicorn
import hashlib
from starlette.applications import Starlette
from starlette.responses import HTMLResponse,PlainTextResponse
from starlette.routing import Route,WebSocketRoute
from starlette.endpoints import WebSocketEndpoint
from starlette.middleware import Middleware
from starlette.requests import HTTPConnection
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from starlette.websockets import WebSocketState

from htag import Tag
from htag.runners import commons

#/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
from . import crypto,serverredys
from .session import Session
from .fqn import findfqn
from .hrclient import HrClient

#/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\

logger = logging.getLogger(__name__)
####################################################

import logging
logging.basicConfig(format='[%(levelname)-7s] --- %(message)s',level=logging.INFO)


parano_seed = lambda uid: hashlib.md5(uid.encode()).hexdigest()

class WebServerSession:  # ASGI Middleware, for starlette
    def __init__(self, app:ASGIApp, https_only:bool = False ) -> None:
        self.app = app
        self.session_cookie = "session"
        self.max_age = 0
        self.path = "/"
        self.security_flags = "httponly; samesite=none"
        if https_only:  # Secure flag can be used with HTTPS only
            self.security_flags += "; secure"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):  # pragma: no cover
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)

        if self.session_cookie in connection.cookies:
            uid = connection.cookies[self.session_cookie]
        else:
            uid = str(uuid.uuid4())

        #!!!!!!!!!!!!!!!!!!!!!!!!!!!
        scope["uid"]     = uid
        scope["session"] = Session(uid)   # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!

        logger.debug("request for %s, scope=%s",uid,scope)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                # send it back, in all cases
                headers = MutableHeaders(scope=message)
                header_value = "{session_cookie}={data}; path={path}; {max_age}{security_flags}".format(  # noqa E501
                    session_cookie=self.session_cookie,
                    data=uid,
                    path=self.path,
                    max_age=f"Max-Age={self.max_age}; " if self.max_age else "",
                    security_flags=self.security_flags,
                )
                headers.append("Set-Cookie", header_value)
            await send(message)

        await self.app(scope, receive, send_wrapper)


# def normalize(fqn):
#     if ":" not in fqn:
#         # replace last "." by ":"
#         fqn="".join( reversed("".join(reversed(fqn)).replace(".",":",1)))
#     return fqn



class HRSocket(WebSocketEndpoint):
    encoding = "text"
    task=None
    async def _sendback(self,websocket, txt:str) -> bool:
        try:
            if self.is_parano:
                seed = parano_seed( websocket.scope["uid"])
                txt = crypto.encrypt(txt.encode(),seed)

            await websocket.send_text( txt )
            return True
        except Exception as e:
            logger.error("%s: ws sendback, error: %s",repr(self.hr),e)
            return False

    async def on_connect(self, websocket):
        fqn=websocket.path_params.get("fqn","")
        uid=websocket.scope["uid"]

        # define hrclient for this socket
        self.hr=HrClient(uid,fqn)

        # define parano mode for this socket
        self.is_parano="parano" in websocket.query_params.keys()

        await websocket.accept()
        async def looper( websocket ):
            try:
                logger.info("%s: WS Runner-LOOP started",repr(self.hr))
                await asyncio.sleep(0.5)    # wait (give the time to establish the connection)
                async for actions in self.hr.updater():
                    if not actions:
                        logger.warning("%s: WS Runner-LOOP breaked (coz empty fifo)",repr(self.hr))
                        break
                    if websocket.application_state==WebSocketState.CONNECTED and websocket.client_state==WebSocketState.CONNECTED:
                        x=await self._sendback( websocket, json.dumps(actions) )
                        if not x:
                            logger.warning("%s: WS Runner-LOOP breaked (coz False response)",repr(self.hr))
                            break
                    else:
                        logger.warning("%s: WS Runner-LOOP breaked (coz WS broken)",repr(self.hr))
                        break

            except Exception as e:
                logger.info("%s: WS Runner-LOOP ERROR: %s",repr(self.hr),e)
            finally:
                logger.info("%s: WS Runner-LOOP stopped",repr(self.hr))

        websocket.task = asyncio.ensure_future( looper(websocket) )


    async def on_receive(self, websocket, data):
        uid=websocket.scope["uid"]
        if self.is_parano:
            data = crypto.decrypt(data.encode(),parano_seed( uid )).decode()
        data=json.loads(data)

        actions=await self.hr.interact( id=data["id"], method=data["method"], args=data["args"], kargs=data["kargs"], event=data.get("event") )

        await self._sendback( websocket, json.dumps(actions) )

    async def on_disconnect(self, websocket, close_code):
        websocket.task.cancel()
        await asyncio.sleep(0.1)

        # NO WAIT the cancellation of the task !!!!!!
        # NO WAIT the cancellation of the task !!!!!!
        # NO WAIT the cancellation of the task !!!!!!
        # try:
        #     await websocket.task
        # except asyncio.CancelledError:
        #     pass        
        # NO WAIT the cancellation of the task !!!!!!
        # NO WAIT the cancellation of the task !!!!!!
        # NO WAIT the cancellation of the task !!!!!!


@contextlib.asynccontextmanager
async def lifespan(app):
    print("--- START")
    await serverredys.start()
    await HrClient.clean()
    yield
    print("--- STOP")
    await HrClient.clean()
    serverredys.stop()


class Runner(Starlette):
    def __init__(self,
                obj:"Tag|fqn|None"=None,
                # session_factory:"sessions.MemDict|sessions.FileDict|sessions.FilePersistentDict|None"=None,
                host="0.0.0.0",
                port=8000,
                debug:bool=False,
                ssl:bool=False,
                parano:bool=False,
                http_only:bool=False,
                timeout_interaction:int=60,
                timeout_inactivity:int=0,
            ):
        self.host=host
        self.port=port
        self.ssl=ssl
        self.parano = parano
        self.http_only = http_only
        self.timeout_interaction = timeout_interaction
        self.timeout_inactivity = timeout_inactivity
        self.fullerror = debug

        ###################################################################

        # exposes ws & http routes in all cases
        routes=[
            Route("/_/{fqn}", self.HRHttp, methods=["POST"]),
            WebSocketRoute("/_/{fqn}", HRSocket)
        ]

        #################################################################
        Starlette.__init__( self,
            debug=debug,
            routes=routes,
            middleware=[Middleware(WebServerSession,https_only=self.ssl)],
            lifespan=lifespan,
        )

        if obj:
            async def handleHome(request):
                return await self.handle(request,obj)
            self.add_route( '/', handleHome )

    # DEPRECATED
    async def serve(self, request,obj:"Tag|fqn",) -> HTMLResponse:
        return await self.handle( request, obj)

    # new method
    async def handle(self, request,
                    obj:"Tag|fqn",
                    http_only:"bool|None"=None,
                    parano:"bool|None"=None,
                    timeout_interaction:"int|None"=None,
                    timeout_inactivity:"int|None"=None,
                    ) -> HTMLResponse:
        # take default behaviour if not present
        is_parano = self.parano if parano is None else parano
        is_http_only = self.http_only if http_only is None else http_only
        the_timeout_interaction = self.timeout_interaction if timeout_interaction is None else timeout_interaction
        the_timeout_inactivity = self.timeout_inactivity if timeout_inactivity is None else timeout_inactivity

        uid = request.scope["uid"]
        init = commons.url2ak(str(request.url))
        fqn=findfqn(obj)

        if is_parano:
            seed = parano_seed( uid )

            jslib = crypto.JSCRYPTO
            jslib += f"\nvar _PARANO_='{seed}'\n"
            jslib += "\nasync function _read_(x) {return await decrypt(x,_PARANO_)}\n"
            jslib += "\nasync function _write_(x) {return await encrypt(x,_PARANO_)}\n"
            pparano="?parano"
        else:
            jslib = ""
            jslib += "\nasync function _read_(x) {return x}\n"
            jslib += "\nasync function _write_(x) {return x}\n"
            pparano=""


        if is_http_only:
            # interactions use HTTP POST
            js = """%(jslib)s

            async function interact( o ) {
                let body = await _write_(JSON.stringify(o));
                let req=await window.fetch("/_/%(fqn)s%(pparano)s",{method:"POST", body: body, mode: 'cors', credentials: 'include', referrerPolicy: "origin"});
                let actions=await req.text();
                action( await _read_(actions) );
            }

            window.addEventListener('DOMContentLoaded', start );
            """ % locals()
        else:
            # interactions use WS
            protocol = "wss" if self.ssl else "ws"

            js = """%(jslib)s

            async function interact( o ) {
                _WS_.send( await _write_(JSON.stringify(o)) );
            }

            // instanciate the WEBSOCKET
            let _WS_=null;
            let retryms=500;

            function connect() {
                _WS_= new WebSocket("%(protocol)s://"+location.host+"/_/%(fqn)s%(pparano)s");
                _WS_.onopen=function(evt) {
                    console.log("** WS connected")
                    document.body.classList.remove("htagoff");
                    retryms=500;
                    start();

                    _WS_.onmessage = async function(e) {
                        let actions = await _read_(e.data)
                        action(actions)
                    };

                }

                _WS_.onclose = function(evt) {
                    console.log("** WS disconnected, retry in (ms):",retryms);
                    document.body.classList.add("htagoff");

                    setTimeout( function() {
                        connect();
                        retryms=retryms*2;
                    }, retryms);
                };
            }
            connect();
            """ % locals()

        hr = HrClient(uid,fqn, the_timeout_interaction, the_timeout_inactivity)
        hr=await hr.create(js=js,init=init,fullerror=self.fullerror)
        html=str(hr)
        return HTMLResponse(html)




    async def HRHttp(self,request) -> PlainTextResponse:
        uid = request.scope["uid"]
        fqn = request.path_params.get("fqn","")
        is_parano="parano" in request.query_params.keys()
        seed = parano_seed( uid )

        hr=HrClient(uid,fqn,self.timeout_interaction,self.timeout_inactivity)
        data = await request.body()

        if is_parano:
            data = crypto.decrypt(data,seed).decode()

        data=json.loads(data)
        actions=await hr.interact( id=data["id"], method=data["method"], args=data["args"], kargs=data["kargs"], event=data.get("event") )
        txt=json.dumps(actions)

        if is_parano:
            txt = crypto.encrypt(txt.encode(),seed)

        return PlainTextResponse(txt)

    def run(self, openBrowser=False):
        if openBrowser:
            import webbrowser
            webbrowser.open_new_tab(f"http://localhost:{self.port}")

        try:
            uvicorn.run(self, host=self.host, port=self.port)
        except KeyboardInterrupt:
            print("---- CTRL-C")        


