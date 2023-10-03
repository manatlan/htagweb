# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import uvicorn
from . import HtagServer
import sys

if __name__=="__main__":
    if len(sys.argv)==1:
        app=HtagServer(None, debug=True)
    elif len(sys.argv)==2:
        app=HtagServer(sys.argv[1], debug=True)
    else:
        print("bad call (only one paremeter is possible (a fqn, ex: 'main:App'))")
        sys.exit(-1)
    app.run(openBrowser=True)
