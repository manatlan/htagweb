# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################


from .appserver import AppServer  # a completly different beast, but compatible with ^^
from .htagserver import HtagServer  # a completly different beast.

__all__= ["AppServer"]

__version__ = "0.0.0" # auto updated
