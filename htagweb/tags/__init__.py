# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

from htag import Tag
import os

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

