# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

from types import ModuleType
import inspect,sys,os
from htag import Tag


def findfqn(x) -> str:
    """ return string like "module.App"  (not with :)"""
    if isinstance(x,str):
        if ("." not in x) and (":" not in x):
            raise Exception(f"'{x}' is not a 'full qualified name' (expected 'module.name') of an App (htag.Tag class)")
        return x.replace(":",".")    # /!\ x is a fqn /!\ DANGEROUS /!\
    elif isinstance(x, ModuleType):
        if hasattr(x,"App"):
            tagClass=getattr(x,"App")
            if not ( inspect.isclass(tagClass) and issubclass(tagClass,Tag) ):
                raise Exception(f"The 'App' of the module '{x}' is not a 'htag.Tag class'")
        else:
            raise Exception("module should contains a 'App' (htag.Tag class)")
    elif inspect.isclass(x) and issubclass(x,Tag):
        tagClass=x
    else:
        raise Exception(f"!!! wtf ({x}) ???")

    if tagClass.__module__=="__main__":
        fullmodule = os.path.splitext(os.path.relpath(inspect.getfile(tagClass)))[0].replace("/",".")
        return fullmodule+"."+tagClass.__qualname__
    else:
        return tagClass.__module__+"."+tagClass.__qualname__


