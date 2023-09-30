# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

# gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b localhost:8000 --preload basic:app


import os
import sys
import json
import uuid
import logging
import uvicorn
import asyncio
import hashlib
import multiprocessing
from htag import Tag
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.applications import Starlette
from starlette.routing import Route,WebSocketRoute
from starlette.endpoints import WebSocketEndpoint
from starlette.middleware import Middleware
from starlette.requests import HTTPConnection
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from htag.runners import commons
from . import crypto
import redys

from htagweb.server import importClassFromFqn, hrserver, hrserver_orchestrator
from htagweb.server.client import HrPilot

logger = logging.getLogger(__name__)
####################################################
from types import ModuleType

from . import sessions

def findfqn(x) -> str:
    if isinstance(x,str):
        if ("." not in x) and (":" not in x):
            raise Exception(f"'{x}' is not a 'full qualified name' (expected 'module.name') of an App (htag.Tag class)")
        return x    # /!\ x is a fqn /!\ DANGEROUS /!\
    elif isinstance(x, ModuleType):
        if hasattr(x,"App"):
            tagClass=getattr(x,"App")
            if not issubclass(tagClass,Tag):
                raise Exception("The 'App' of the module is not inherited from 'htag.Tag class'")
        else:
            raise Exception("module should contains a 'App' (htag.Tag class)")
    elif issubclass(x,Tag):
        tagClass=x
    else:
        raise Exception(f"!!! wtf ({x}) ???")

    return tagClass.__module__+"."+tagClass.__qualname__


class WebServerSession:  # ASGI Middleware, for starlette
    def __init__(self, app:ASGIApp, https_only:bool = False, sesprovider:"async method(uid)"=None ) -> None:
        self.app = app
        self.session_cookie = "session"
        self.max_age = 0
        self.path = "/"
        self.security_flags = "httponly; samesite=lax"
        if https_only:  # Secure flag can be used with HTTPS only
            self.security_flags += "; secure"
        self.cbsesprovider=sesprovider

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
        scope["parano"]  = hashlib.md5(uid.encode()).hexdigest()
        scope["session"] = await self.cbsesprovider(uid)
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


def normalize(fqn):
    if ":" not in fqn:
        # replace last "." by ":"
        fqn="".join( reversed("".join(reversed(fqn)).replace(".",":",1)))
    return fqn



class HRSocket(WebSocketEndpoint):
    encoding = "text"

    async def _sendback(self,websocket, txt:str) -> bool:
        parano_seed = websocket.scope["parano"] if websocket.app.parano else None
        try:
            if parano_seed:
                txt = crypto.encrypt(txt.encode(),parano_seed)

            await websocket.send_text( txt )
            return True
        except Exception as e:
            logger.error("Can't send to socket, error: %s",e)
            return False

    async def loop_tag_update(self, event, websocket):
        with redys.AClient() as bus:
            await bus.subscribe(event)

            ok=True
            while ok:
                actions = await bus.get_event( event )
                if actions:
                    ok=await self._sendback(websocket,json.dumps(actions))
                await asyncio.sleep(0.1)

    async def on_connect(self, websocket):
        #====================================================== get the event
        fqn=websocket.path_params.get("fqn","")
        uid=websocket.scope["uid"]
        event=HrPilot(uid,fqn).event_response+"_update"
        #======================================================

        # asyncio.ensure_future(self.loop_tag_update(event,websocket))

        await websocket.accept()

    async def on_receive(self, websocket, data):
        fqn=websocket.path_params.get("fqn","")
        uid=websocket.scope["uid"]
        parano_seed = websocket.scope["parano"] if websocket.app.parano else None

        if parano_seed:
            data = crypto.decrypt(data.encode(),parano_seed).decode()
        data=json.loads(data)

        p=HrPilot(uid,fqn)

        actions=await p.interact( oid=data["id"], method_name=data["method"], args=data["args"], kargs=data["kargs"], event=data.get("event") )

        await self._sendback( websocket, json.dumps(actions) )

    async def on_disconnect(self, websocket, close_code):
        #====================================================== get the event
        fqn=websocket.path_params.get("fqn","")
        uid=websocket.scope["uid"]
        event=HrPilot(uid,fqn).event_response+"_update"
        #======================================================

        with redys.AClient() as bus:
            await bus.unsubscribe(event)


def processHrServer():
    asyncio.run( hrserver() )


class AppServer(Starlette):   #NOT THE DEFINITIVE NAME !!!!!!!!!!!!!!!!
    def __init__(self,obj:"htag.Tag class|fqn|None"=None, debug:bool=True,ssl:bool=False,parano:bool=False,sesprovider:"htagweb.sessions.create*|None"=None):
        self.ssl=ssl
        self.parano=parano

        if sesprovider is None:
            self.sesprovider = sessions.createFile
        else:
            self.sesprovider =  sesprovider

        print("Session with:",self.sesprovider.__name__)
        ###################################################################

        p=multiprocessing.Process(target=processHrServer)
        p.start()

        #################################################################
        Starlette.__init__( self,
            debug=debug,
            routes=[WebSocketRoute("/_/{fqn}", HRSocket)],
            middleware=[Middleware(WebServerSession,https_only=ssl,sesprovider=self.sesprovider)],
        )

        if obj:
            async def handleHome(request):
                return await self.serve(request,obj)
            self.add_route( '/', handleHome )

    async def serve(self, request, obj ) -> HTMLResponse:
        uid = request.scope["uid"]
        parano_seed = request.scope["parano"] if self.parano else None

        fqn=normalize(findfqn(obj))

        protocol = "wss" if self.ssl else "ws"

        if parano_seed:
            jsparano = crypto.JSCRYPTO
            jsparano += f"\nvar _PARANO_='{parano_seed}'\n"
            jsparano += "\nasync function _read_(x) {return await decrypt(x,_PARANO_)}\n"
            jsparano += "\nasync function _write_(x) {return await encrypt(x,_PARANO_)}\n"
        else:
            jsparano = ""
            jsparano += "\nasync function _read_(x) {return x}\n"
            jsparano += "\nasync function _write_(x) {return x}\n"


        js = """
%(jsparano)s

async function interact( o ) {
    _WS_.send( await _write_(JSON.stringify(o)) );
}

// instanciate the WEBSOCKET
let _WS_=null;
let retryms=500;

function connect() {
    _WS_= new WebSocket("%(protocol)s://"+location.host+"/_/%(fqn)s");
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

        p = HrPilot(uid,fqn,js,self.sesprovider.__name__)

        args,kargs = commons.url2ak(str(request.url))
        html=await p.start(*args,**kargs)
        return HTMLResponse(html or "no?!")



    def run(self, host="0.0.0.0", port=8000, openBrowser=False):   # localhost, by default !!
        if openBrowser:
            import webbrowser
            webbrowser.open_new_tab(f"http://localhost:{port}")

        uvicorn.run(self, host=host, port=port)
