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

####################################################
class IndexApp(Tag.body):
    statics="""
    * {font-family: sans-serif;}
    .file,.folder {margin-left:8px}
    .file *,.folder * {text-decoration: none}
    .folder * {font-weight:800}
    """
    imports=[]

    def init(self,path="."):
        if path.strip().startswith( ("/","\\" )) or ".." in path:
            self += "?!"
        else:
            olist=Tag.div()

            folders=[]
            files=[]
            for i in os.listdir(path):
                if i.startswith( (".","_") ): continue
                if os.path.isdir( os.path.join(path,i) ):
                    folders.append( (i,os.path.join(path,i)) )
                elif i.lower().endswith(".py"):
                    files.append( (i, f"{path.replace(os.sep,'.')}.{i[:-3]}".strip(".")))

            for i,fp in sorted(folders):
                olist+= Tag.div( Tag.a( f"📂 {i}",_href="?"+fp ), _class="folder")
            for i,fp in sorted(files):
                olist+= Tag.div( Tag.a(i,_href=fp), _class="file")

            self+= Tag.h3(f"Folder {path}")
            self+= olist

####################################################

class HtagServer(SimpleServer):
    def __init__(self,obj:"htag.Tag class|fqn|None"=None, *a,**k):
        if obj is None:
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
