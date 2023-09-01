# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################


"""
WebServer & WebServerWS
~~~~~~~~~~~~~~~~~~~~~~~~
- new versions of oldest WebHTTP & WebWS (nearly compatibles)
- concept of an htag app application server (manager), which communicate with child process, with queue
- Htag Apps runned in a process, per user (real isolation!)
- when session expire (after inactivity timeout), child process are destroyed
- works with multiple uvicorn webworkers, and uvloop
- WebServerWS use ws/wss sockets to interact (instead of http/post)
- 30s timeout for interactions/render times
- TODO: parano mode (aes encryption in exchanges)
"""
import uvicorn
import json,os
from types import ModuleType
import uuid,logging
import contextlib

from htag import Tag
from htag.runners import commons

from starlette.applications import Starlette
from starlette.responses import HTMLResponse,PlainTextResponse
from starlette.routing import Route,WebSocketRoute
from starlette.endpoints import WebSocketEndpoint
from starlette.middleware import Middleware
from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

#=-=-=-=-=-=-
from .manager import Manager
from .uidprocess import Users
from .crypto import decrypt,encrypt,JSCRYPTO
#=-=-=-=-=-=-

logger = logging.getLogger(__name__)
#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=

# python3 -m pytest --cov-report html --cov=htagweb .



@contextlib.asynccontextmanager
async def htagweb_life(app):
    async with Manager() as m:
        app.state.manager = m
        pid=os.getpid()
        logger.info("Startup [%s] %s",pid,m.is_server() and "***MANAGER RUNNED***" or "")
        yield
        logger.info("Stopping [%s]",pid)


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
            uid = str(uuid.uuid4())

        #!!!!!!!!!!!!!!!!!!!!!!!!!!!
        scope["uid"] = uid
        scope["session"] = Users.use(uid).session   # CREATE a session if uid not known
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


class WebBase(Starlette):

    def __init__(self,obj=None,timeout=5*60, routes=None):
        # self.crypt="test"   # or None
        self.crypt=None

        Starlette.__init__(self,debug=True, lifespan=htagweb_life,routes=routes,middleware=[Middleware(WebServerSession)])

        if obj:
            async def handleHome(request):
                return await self.serve(request,obj)
            self.add_route( '/', handleHome )


    def run(self, host="0.0.0.0", port=8000, openBrowser=False):   # localhost, by default !!
        if openBrowser:
            import webbrowser
            webbrowser.open_new_tab(f"http://localhost:{port}")

        uvicorn.run(self, host=host, port=port)


    async def interact(self,uid:str,fqn:str,query:str) -> str:
        data = self._str2dict( query )
        actions = await self.state.manager.ht_interact(uid,fqn,data)
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
        html = await request.app.state.manager.ht_create(uid, fqn, fjs, init_params, renew=renew)
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

