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
import inspect
import logging
import uvicorn
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

from htag.render import HRenderer
from htag.runners import commons
from . import crypto

logger = logging.getLogger(__name__)
####################################################

# reuse some things from htagserver ;-)
from .htagserver import WebServerSession,getClass
from .webbase import findfqn


def fqn2hr(fqn:str,js:str,init,session): # fqn is a "full qualified name", full !
    if ":" not in fqn:
        # replace last "." by ":"
        fqn="".join( reversed("".join(reversed(fqn)).replace(".",":",1)))

    klass=getClass(fqn)

    return HRenderer( klass, js, init=init, session = session)

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
            hr=fqn2hr(fqn,js,commons.url2ak(str(websocket.url)),websocket.session)
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
        actions = await self.hr.interact(data["id"],data["method"],data["args"],data["kargs"],data.get("event"))
        await self._sendback( websocket, json.dumps(actions) )

    async def on_disconnect(self, websocket, close_code):
        del self.hr

class AppServer(Starlette):
    def __init__(self,obj:"htag.Tag class|fqn|None"=None, debug:bool=True,ssl:bool=False,session_size:int=10240,parano:bool=False):
        self.ssl=ssl
        self.parano = str(uuid.uuid4()) if parano else None
        Starlette.__init__( self,
            debug=debug,
            routes=[WebSocketRoute("/_/{fqn}", HRSocket)],
            middleware=[Middleware(WebServerSession,https_only=ssl,session_size=session_size)],
        )

        if obj:
            async def handleHome(request):
                return await self.serve(request,obj)
            self.add_route( '/', handleHome )

    async def serve(self, request, obj, **NONUSED ) -> HTMLResponse:
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
            var _WS_ = new WebSocket("%(protocol)s://"+location.host+"/_/%(fqn)s"+location.search);
            _WS_.onmessage = async function(e) {
                // when connected -> the full HTML page is returned, installed & start'ed !!!

                let html = await _read_(e.data);
                html = html.replace("<body ","<body onload='start()' ");

                document.open();
                document.write(html);
                document.close();
            };
        """ % locals()

        # here return a first rendering (only for SEO)
        # the hrenderer is DESTROYED just after
        hr=fqn2hr(fqn,jsbootstrap,commons.url2ak(str(request.url)),request.session)

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
