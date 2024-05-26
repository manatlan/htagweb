# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2024 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

__version__ = "0.0.0" # auto updated

from .runners import Runner
from .runners import Runner as AppServer # for compatibility with htagweb <=0.24


__all__= ["Runner"]
