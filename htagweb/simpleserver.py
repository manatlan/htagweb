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
import logging
import uvicorn
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

logger = logging.getLogger(__name__)
####################################################

from . import sessions
from .appserver import WebServerSession,findfqn
from .server import importClassFromFqn


def fqn2hr(fqn:str,js:str,init,session,fullerror=False): # fqn is a "full qualified name", full !
    if ":" not in fqn:
        # replace last "." by ":"
        fqn="".join( reversed("".join(reversed(fqn)).replace(".",":",1)))

    klass=importClassFromFqn(fqn)

    styles=Tag.style("body.htagoff * {cursor:not-allowed !important;}")

    return HRenderer( klass, js, init=init, session = session, fullerror=fullerror, statics=[styles,])

class HRSocket(WebSocketEndpoint):
    encoding = "text"

    async def _sendback(self,ws, txt:str) -> bool:
        try:
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

        data=json.loads(data)

        #=================================== for UT only
        if data["id"]=="ut":
            data["id"]=id(self.hr.tag)
        #===================================

        actions = await self.hr.interact(data["id"],data["method"],data["args"],data["kargs"],data.get("event"))
        await self._sendback( websocket, json.dumps(actions) )

    async def on_disconnect(self, websocket, close_code):
        del self.hr

class SimpleServer(Starlette):
    def __init__(self,obj:"htag.Tag class|fqn|None"=None, debug:bool=True):
        sesprovider = sessions.FileDict

        Starlette.__init__( self,
            debug=debug,
            routes=[WebSocketRoute("/_/{fqn}", HRSocket)],
            middleware=[Middleware(WebServerSession,https_only=False,sesprovider=sesprovider)],
        )

        if obj:
            async def handleHome(request):
                return await self.serve(request,obj)
            self.add_route( '/', handleHome )

    async def serve(self, request, obj ) -> HTMLResponse:
        fqn=findfqn(obj)
        protocol = "ws"

        jsinc = ""
        jsinc += "\nasync function _read_(x) {return x}\n"
        jsinc += "\nasync function _write_(x) {return x}\n"

        jsbootstrap="""
            %(jsinc)s
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


    def run(self, host="0.0.0.0", port=8000, openBrowser=False):   # localhost, by default !!
        if openBrowser:
            import webbrowser
            webbrowser.open_new_tab(f"http://localhost:{port}")

        uvicorn.run(self, host=host, port=port)
