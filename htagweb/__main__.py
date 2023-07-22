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

app=HtagServer(debug=True,ssl=False)
if __name__=="__main__":
    uvicorn.run(app)
