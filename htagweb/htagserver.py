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
This thing is HtagServer, but with 2 majors behaviour

- If "no klass"(None) is defined -> will hook "/" on IndexApp (a browser of folders/files)
- every others routes -> will try to instanciate an htag app

"""


import os

from starlette.responses import HTMLResponse,Response

from htag import Tag
from .simpleserver import SimpleServer
from .server import importClassFromFqn

class HtagServer(SimpleServer):
    
    
    def __init__(self,obj:"htag.Tag|fqn|None"=None, *a,**k):
        if obj is None:
            from htagweb.tags import IndexApp
            obj = IndexApp
        SimpleServer.__init__(self,obj,*a,**k)

        self.add_route('/{path}', self._serve)

    async def _serve(self, request) -> HTMLResponse:
        fqn=request.path_params.get("path","").strip() #can't contain ":"

        fqn_norm="".join( reversed("".join(reversed(fqn)).replace(".",":",1)))

        try:
            klass=importClassFromFqn(fqn_norm)
        except:
            try:
                klass=importClassFromFqn(fqn+":App")
            except ModuleNotFoundError:
                return HTMLResponse("Not Found (%s)" % fqn,404,media_type="text/plain")

        return await self.serve(request,klass)
