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
This thing is completly new, and doesn't work as all classic runners.

Concepts are totally differents ;-)

    - It's REALLY not good for SEO (because firts html page is a bootstrap html page (technical page))
    - because a Hrenderer lives in a socket connection only (a lot lot lot simpler)
      (tags live during a socket session)

So, hitting "F5" -> will recreate hrenderer/htag
    - So, it will support OOTB reloading (during dev phase : great!)

BTW, it support all web/htag features :
    - multiple uvicorn web worker
    - uvloop
    - session by user.
    - sharing session accross multiple webworker
    - tag.update()
    - parano mode

So, if you need to store things, use the session or a db mechanism.

and mainly : it can serve htag's app that are in the filesystem 'examples.app1:App' or 'examples.app1' (if it contains an 'App' class)
if it doesn't found a "index:App", it will provide its default one, let you browse python files in the current folder.

so, in console : "python3 -m htagweb" will run a uvicorn webworker, and expose yours python file on http/ws
"""


import os
import sys
import json
import uuid
import inspect
import logging
import importlib

from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.applications import Starlette
from starlette.routing import Route,WebSocketRoute
from starlette.endpoints import WebSocketEndpoint
from starlette.middleware import Middleware
from starlette.requests import HTTPConnection
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from shared_memory_dict import SharedMemoryDict

from htag import Tag
from htag.render import HRenderer
from htag.runners import commons
from . import crypto

logger = logging.getLogger(__name__)
####################################################
class IndexApp(Tag.div):
    imports=[]

    def init(self,path="."):
        assert ".." not in path
        assert not path.strip().startswith("/")
        assert not path.strip().startswith("\\")

        olist=Tag.div()

        for i in os.listdir(path):
            if os.path.isdir( os.path.join(path,i) ):
                fp=os.path.join(path,i)
                olist+= Tag.li( Tag.a( Tag.b(f"[{i}]"),_href="?path="+fp ))
        for i in os.listdir(path):
            if i.lower().endswith(".py"):
                fp=f"{path.replace(os.sep,'.')}.{i[:-3]}".strip(".")
                olist+= Tag.li( Tag.A(i,_href=fp))

        self+= Tag.h3(f"Folder {path}")
        self+= olist

####################################################



class WebServerSession:  # ASGI Middleware, for starlette
    def __init__(self, app:ASGIApp, https_only:bool = False, session_size:int=10240 ) -> None:
        self.app = app
        self.session_cookie = "session"
        self.max_age = 0
        self.path = "/"
        self.security_flags = "httponly; samesite=lax"
        if https_only:  # Secure flag can be used with HTTPS only
            self.security_flags += "; secure"
        self.session_size=session_size

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
        scope["session"] = SharedMemoryDict(name=uid, size=self.session_size)
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



def getClass(fqn:str) -> type:
    assert ":" in fqn
    #--------------------------- fqn -> module, name
    modulename,name = fqn.split(":",1)
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
        raise Exception(f"'{fqn}' is not a htag.Tag subclass")
    return klass

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
        path=websocket.path_params.get("path","")

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
        self.hr=None

        if not path:
            try:
                klass=getClass("index:App")
            except Exception as e:
                klass=IndexApp
        else:
            try:
                if ":" in path:
                    klass=getClass(path)
                else:
                    klass=getClass(path+":App")
            except Exception as e:
                await self._sendback( websocket, str(e) )
                await websocket.close()
                return

        self.hr=HRenderer(
            klass,
            js,
            init=commons.url2ak(str(websocket.url)),
            session = websocket.session
        )

        # send back the full rendering (1st onmessage after js connection)
        await self._sendback( websocket, str(self.hr) )

        # register the hr.sendactions, for tag.update feature
        self.hr.sendactions=lambda actions: self._sendback(websocket,json.dumps(actions))

    async def on_receive(self, websocket, data):
        if websocket.app.parano:
            data = crypto.decrypt(data.encode(),websocket.app.parano).decode()

        data=json.loads(data)
        actions = await self.hr.interact(data["id"],data["method"],data["args"],data["kargs"],data.get("event"))
        await self._sendback( websocket, json.dumps(actions) )

    async def on_disconnect(self, websocket, close_code):
        del self.hr

class HtagServer(Starlette):
    def __init__(self,debug:bool=True,ssl:bool=False,session_size:int=10240,parano:bool=False):
        self.ssl=ssl
        self.parano = str(uuid.uuid4()) if parano else None
        Starlette.__init__( self,
            debug=debug,
            routes=[
                Route('/', self._servehtagapp),
                Route('/{path}', self._servehtagapp),
                WebSocketRoute("/_WS_/", HRSocket),
                WebSocketRoute("/_WS_/{path}", HRSocket),
            ],
            middleware=[Middleware(WebServerSession,https_only=ssl,session_size=session_size)],
        )

    async def _servehtagapp(self,request):
        path=request.path_params.get("path","")
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
        bootstrapHtmlPage="""<!DOCTYPE html>
            <html>
              <head>
                    <script>
                    %(jsparano)s
                    // instanciate the WEBSOCKET
                    var _WS_ = new WebSocket("%(protocol)s://"+location.host+"/_WS_/%(path)s"+location.search);
                    _WS_.onmessage = async function(e) {
                        // when connected -> the full HTML page is returned, installed & start'ed !!!

                        let html = await _read_(e.data);
                        html = html.replace("<body ","<body onload='start()' ");

                        document.open();
                        document.write(html);
                        document.close();
                    };
                    </script>
              </head>
              <body>loading</body>
            </html>
            """ % locals()

        return HTMLResponse( bootstrapHtmlPage )


