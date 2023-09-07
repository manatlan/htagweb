# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

from .file import create as createFile
from .shm import create as createShm
from .shm import create as createMem

__all__= ["createFile","createShm","createMem"]