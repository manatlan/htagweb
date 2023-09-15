# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

# gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b localhost:8000 --preload basic:app

"""
IDEM que htagweb.AppServer
- mais sans le SHARED MEMORY DICT (donc compat py3.7) ... grace au sesprovider !
- fichier solo
- !!! utilise crypto de htagweb !!!



This thing is completly new different beast, and doesn't work as all classic runners.

It's a runner between "WebHTTP/WebServer" & "HtagServer" : the best of two worlds

    - It's fully compatible with WebHTTP/WebServer (provide a serve method)
    - it use same techs as HTagServer (WS only, parano mode, simple/#workers, etc ...)
    - and the SEO trouble is faked by a pre-fake-rendering (it create a hr on http, for seo ... and recreate a real one at WS connect)

Like HTagServer, as lifespan of htag instances is completly changed :
htag instances should base their state on "self.root.state" only!
Because a F5 will always destroy/recreate the instance.
"""

import os
import sys
import json
import uuid
import pickle
import inspect
import logging
import uvicorn
import importlib
import contextlib
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

from htag.render import HRenderer
from htag.runners import commons
from . import crypto,usot

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

def getClass(fqn_norm:str) -> type:
    assert ":" in fqn_norm
    #--------------------------- fqn -> module, name
    modulename,name = fqn_norm.split(":",1)
    if modulename in sys.modules:
        module=sys.modules[modulename]
        try:
            module=importlib.reload( module )
        except ModuleNotFoundError:
            """ can't be (really) reloaded if the component is in the
            same module as the instance htag server"""
            pass
    else:
        module=importlib.import_module(modulename)
    #---------------------------
    klass= getattr(module,name)
    if not ( inspect.isclass(klass) and issubclass(klass,Tag) ):
        raise Exception(f"'{fqn_norm}' is not a htag.Tag subclass")

    if not hasattr(klass,"imports"):
        # if klass doesn't declare its imports
        # we prefer to set them empty
        # to avoid clutering
        klass.imports=[]
    return klass


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


def fqn2hr(fqn:str,js:str,init,session,fullerror=False): # fqn is a "full qualified name", full !
    if ":" not in fqn:
        # replace last "." by ":"
        fqn="".join( reversed("".join(reversed(fqn)).replace(".",":",1)))

    klass=getClass(fqn)

    styles=Tag.style("body.htagoff * {cursor:not-allowed !important;}")

    return HRenderer( klass, js, init=init, session = session, fullerror=fullerror, statics=[styles,])

class HRSocket(WebSocketEndpoint):
    encoding = "text"

    async def _sendback(self,ws, txt:str) -> bool:
        try:
            if ws.app.parano:
                txt = crypto.encrypt(txt.encode(),ws.app.parano)

            await ws.send_text( txt )
            return True
        except Exception as e:
            logger.error("Can't send to socket, error: %s",e)
            return False

    async def on_connect(self, websocket):
        fqn=websocket.path_params.get("fqn","")

        await websocket.accept()
        js="""
// rewrite the onmessage of the _WS_ to interpret json action now !
_WS_.onmessage = async function(e) {
    let actions = await _read_(e.data)
    action(actions)
}

// declare the interact js method to communicate thru the WS
async function interact( o ) {
    _WS_.send( await _write_(JSON.stringify(o)) );
}

console.log("started")
"""

        try:
            hr=fqn2hr(fqn,js,commons.url2ak(str(websocket.url)),websocket.session,fullerror=websocket.app.debug)
        except Exception as e:
            await self._sendback( websocket, str(e) )
            await websocket.close()
            return

        self.hr=hr

        # send back the full rendering (1st onmessage after js connection)
        await self._sendback( websocket, str(self.hr) )

        # register the hr.sendactions, for tag.update feature
        self.hr.sendactions=lambda actions: self._sendback(websocket,json.dumps(actions))

    async def on_receive(self, websocket, data):
        if websocket.app.parano:
            data = crypto.decrypt(data.encode(),websocket.app.parano).decode()

        data=json.loads(data)

        #=================================== for UT only
        if data["id"]=="ut":
            data["id"]=id(self.hr.tag)
        #===================================

        actions = await self.hr.interact(data["id"],data["method"],data["args"],data["kargs"],data.get("event"))
        await self._sendback( websocket, json.dumps(actions) )

    async def on_disconnect(self, websocket, close_code):
        del self.hr

class AppServer(Starlette):
    def __init__(self,obj:"htag.Tag class|fqn|None"=None, debug:bool=True,ssl:bool=False,parano:bool=False,sesprovider:"htagweb.sessions.create*|None"=None):
        self.ssl=ssl
        self.parano = str(uuid.uuid4()) if parano else None
        if sesprovider is None:
            sesprovider = sessions.createFile
        Starlette.__init__( self,
            debug=debug,
            routes=[WebSocketRoute("/_/{fqn}", HRSocket)],
            middleware=[Middleware(WebServerSession,https_only=ssl,sesprovider=sesprovider)],
        )

        if obj:
            async def handleHome(request):
                return await self.serve(request,obj)
            self.add_route( '/', handleHome )

    async def serve(self, request, obj ) -> HTMLResponse:
        fqn=findfqn(obj)
        protocol = "wss" if self.ssl else "ws"
        if self.parano:
            jsparano = crypto.JSCRYPTO
            jsparano += f"\nvar _PARANO_='{self.parano}'\n"
            jsparano += "\nasync function _read_(x) {return await decrypt(x,_PARANO_)}\n"
            jsparano += "\nasync function _write_(x) {return await encrypt(x,_PARANO_)}\n"
        else:
            jsparano = ""
            jsparano += "\nasync function _read_(x) {return x}\n"
            jsparano += "\nasync function _write_(x) {return x}\n"
        #TODO: consider https://developer.chrome.com/blog/removing-document-write/

        jsbootstrap="""
            %(jsparano)s
            // instanciate the WEBSOCKET
            let _WS_=null;
            let retryms=500;
            
            function connect() {
                _WS_= new WebSocket("%(protocol)s://"+location.host+"/_/%(fqn)s"+location.search);
                _WS_.onopen=function(evt) {
                    console.log("** WS connected")
                    document.body.classList.remove("htagoff");
                    retryms=500;
                    
                    _WS_.onmessage = async function(e) {
                        // when connected -> the full HTML page is returned, installed & start'ed !!!

                        let html = await _read_(e.data);
                        html = html.replace("<body ","<body onload='start()' ");

                        document.open();
                        document.write(html);
                        document.close();
                    };
                }
                
                _WS_.onclose = function(evt) {
                    console.log("** WS disconnected");
                    //console.log("** WS disconnected, retry in (ms):",retryms);
                    document.body.classList.add("htagoff");

                    //setTimeout( function() {
                    //    connect();
                    //    retryms=retryms*2;
                    //}, retryms);
                };
            }
            connect();
        """ % locals()

        # here return a first rendering (only for SEO)
        # the hrenderer is DESTROYED just after
        hr=fqn2hr(fqn,jsbootstrap,commons.url2ak(str(request.url)),request.session, fullerror=self.debug)

        return HTMLResponse( str(hr) )

        # bootstrapHtmlPage="""<!DOCTYPE html>
        #     <html>
        #       <head>
        #             <script>
        #             %(jsparano)s
        #             // instanciate the WEBSOCKET
        #             var _WS_ = new WebSocket("%(protocol)s://"+location.host+"/_/%(fqn)s"+location.search);
        #             _WS_.onmessage = async function(e) {
        #                 // when connected -> the full HTML page is returned, installed & start'ed !!!

        #                 let html = await _read_(e.data);
        #                 html = html.replace("<body ","<body onload='start()' ");

        #                 document.open();
        #                 document.write(html);
        #                 document.close();
        #             };
        #             </script>
        #       </head>
        #       <body>loading</body>
        #     </html>
        #     """ % locals()

        # return HTMLResponse( bootstrapHtmlPage )

    def run(self, host="0.0.0.0", port=8000, openBrowser=False):   # localhost, by default !!
        if openBrowser:
            import webbrowser
            webbrowser.open_new_tab(f"http://localhost:{port}")

        uvicorn.run(self, host=host, port=port)
