# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htag
# #############################################################################

__version__ = "0.0.0" # auto updated

try:
    import uvloop
    raise Exception("htagweb is not compatible with uvloop")
except ImportError:
    pass

"""
WebServer & WebServerWS
~~~~~~~~~~~~~~~~~~~~~~~~
- new versions of oldest WebHTTP & WebWS (nearly compatibles)
- concept of an htag app application server (manager), which communicate with child process, with queue (web workers communicate with the manager using tcp socket)
- Htag App runned in its own process, per user (real isolation!)
- htag app can exit with .exit() (process killed)
- when session expire (after inactivity timeout), child process are destroyed
- real shared session by user (really isolated!)
- works with multiple uvicorn webworkers
- WebServerWS use ws/wss sockets to interact (instead of http/post)
- 30s timeout for interactions/render times
- parano mode (aes encryption in exchanges)
"""
import uvicorn

from htag import Tag
from htag.render import HRenderer
from htag.runners import commons

from starlette.applications import Starlette
from starlette.responses import HTMLResponse,JSONResponse,PlainTextResponse
from starlette.routing import Route,WebSocketRoute
from starlette.endpoints import WebSocketEndpoint

#=-=-=-=-=-=-
from . import shm
from .manager import Manager
from .crypto import decrypt,encrypt,JSCRYPTO
#=-=-=-=-=-=-

import os
import json
import asyncio,pickle
from types import ModuleType
from datetime import datetime

#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=
import json
import sys
import uuid

from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class WebServerSession:  # ASGI Middleware, for starlette
    def __init__(
        self,
        app: ASGIApp,
        https_only: bool = False,
    ) -> None:
        self.app = app
        self.session_cookie = "session"
        self.max_age = 0
        self.path = "/"
        self.security_flags = "httponly; samesite=lax"
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
            uid=str(uuid.uuid4())

        #!!!!!!!!!!!!!!!!!!!!!!!!!!!
        scope["uid"] = uid
        scope["session"] = shm.session(uid) # create a smd

        # declare session
        glob=shm.wses()
        glob[uid]=datetime.now()
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!

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

#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=
def startManager(port,timeout): #sec (timeout session)
    Manager(port).run(timeout)
#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=


class ManagerClient:
    def __init__(self,port):
        self.port=port

    def __getattr__(self,name:str):
        async def _(*a,**k):
            reader, writer = await asyncio.open_connection("127.0.0.1", self.port)

            question = pickle.dumps( (name,a,k) )
            # logger.debug('Sending data of size: %s',len(question))
            writer.write(question)

            await writer.drain()
            writer.write_eof()

            data = await reader.read()
            # logger.debug('recept data of size: %s',len(data))
            reponse = pickle.loads( data )
            if isinstance(reponse,Exception):
                raise reponse

            writer.close()
            await writer.wait_closed()
            return reponse
        return _




def findfqn(x) -> str:
    if isinstance(x,str):
        if "." not in x:
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

class WebBase(Starlette):

    def __init__(self,obj=None,timeout=5*60, routes=None):
        # self.crypt="test"   # or None
        self.crypt=None

        port=27777 # manager server port
        self.manager = ManagerClient(port)

        async def _startManager():
            import multiprocessing
            p = multiprocessing.Process(target=startManager,args=(port,timeout,),name="ManagerServer")
            p.start()

        Starlette.__init__(self,debug=True, on_startup=[_startManager,],routes=routes)

        if obj:
            async def handleHome(request):
                return await self.serve(request,obj)
            self.add_route( '/', handleHome )

        Starlette.add_middleware(self,WebServerSession )


    def run(self, host="0.0.0.0", port=8000, openBrowser=False):   # localhost, by default !!
        if openBrowser:
            import webbrowser
            webbrowser.open_new_tab(f"http://localhost:{port}")

        uvicorn.run(self, host=host, port=port)


    async def interact(self,uid:str,fqn:str,query:str) -> str:
        data = self._str2dict( query )
        actions = await self.manager.ht_interact(uid, fqn, data )
        if isinstance(actions,dict):
            return self._dict2str( actions )
        else:
            return ""   # manager on dead objects/session

    async def render(self,request, uid:str,fqn:str,js:str,renew:bool) -> str:

        if self.crypt:
            fjs = """
%s
async function str2dict(s) { return JSON.parse( await decrypt(s,'%s' )); }
async function dict2str(d) { return await encrypt( JSON.stringify(d), '%s'); }
%s
            """ % (JSCRYPTO,self.crypt,self.crypt,js)
        else:
            fjs = """
async function str2dict(s) { return JSON.parse(s); }
async function dict2str(d) { return JSON.stringify(d); }
            """+js

        init_params = commons.url2ak( str(request.url) )
        html = await self.manager.ht_render(uid,fqn,init_params, fjs, renew )

        return html

    def _dict2str(self,dico:dict) -> str:
        if self.crypt:
            return encrypt( json.dumps(dico).encode() , self.crypt)
        else:
            return json.dumps(dico)

    def _str2dict(self,jzon:str) -> dict:
        if self.crypt:
            return json.loads( decrypt(jzon.encode(), self.crypt) )
        else:
            return json.loads(jzon)

# ###########################################################################
class WebServer(WebBase):
# ###########################################################################
    """ Like WebHTTP, but a lot better """
    def __init__(self,obj=None, timeout=5*60):
        """ obj can be a module (which contain a 'App' (tagClass)) on a tagClass (like before)"""
        WebBase.__init__(self,obj,timeout,[Route('/{fqn:str}', self.POST, methods=["POST"])] )

    async def serve(self,request, obj, renew=False ) -> HTMLResponse:
        # assert obj is correct type
        uid=request.scope["uid"]    # WebServerSession made that possible
        fqn=findfqn(obj)

        js = """
async function interact( o ) {
    let q=await dict2str(o);
    let r=await (await window.fetch("/%s",{method:"POST", body:q})).text();
    if(r!="")
        action( await str2dict(r) );
    else {
        let dsreload=confirm("dead session, reload?");
        if(dsreload) document.location.reload(true);
    }
}

window.addEventListener('DOMContentLoaded', start );
""" % fqn

        html = await self.render(request,uid,fqn, js,renew )
        return HTMLResponse( html )

    async def POST(self,request) -> PlainTextResponse:
        uid=request.scope["uid"]    # WebServerSession made that possible
        fqn=request.path_params.get('fqn',None)

        query=await request.body()
        response = await self.interact(uid, fqn, query.decode() )
        return PlainTextResponse( response )



# ###########################################################################
class WebServerWS(WebBase):
# ###########################################################################
    """ Like WebWS, but a lot better """

    def __init__(self,obj=None, timeout=5*60,wss:bool=False):
        """ obj can be a module (which contain a 'App' (tagClass)) or a tagClass (like before), or a string/fqn"""
        self.wss=wss

        class WsInteract(WebSocketEndpoint):
            # encoding = "json"
            encoding = "text"

            async def on_receive(this, websocket, query:str):
                uid=websocket.scope["uid"]    # WebServerSession made that possible
                fqn=websocket.query_params['fqn']

                response = await self.interact(uid, fqn, query )
                await websocket.send_text( response )

        WebBase.__init__(self,obj,timeout,[WebSocketRoute("/ws", WsInteract)] )

    async def serve(self,request, obj, renew=False ) -> HTMLResponse:
        # assert obj is correct type
        fqn=findfqn(obj)

        uid=request.scope["uid"]    # WebServerSession made that possible

        js = """
async function interact( o ) {
    ws.send( await dict2str(o) );
}

var ws = new WebSocket("%s://"+document.location.host+"/ws?fqn=%s");
ws.onopen = start;
ws.onmessage = async function(e) {
    if(e.data!="")
        action( await str2dict(e.data) );
    else {
        let dsreload=confirm("dead session, reload?");
        if(dsreload) document.location.reload(true);
    }

};
""" % (
    "wss" if self.wss else "ws",
    fqn,
)
        html = await self.render(request,uid,fqn, js,renew )
        return HTMLResponse( html )


