# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2024 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################
import asyncio
try:
    import redys.v2

    _S = None

    ##################################################################################
    async def start():
    ##################################################################################
        global _S
        # start a redys server (only one will win)
        _S=redys.v2.ServerProcess()

        # wait redys up
        bus=redys.v2.AClient()
        while 1:
            try:
                if await bus.ping()=="pong":
                    break
            except:
                pass
            await asyncio.sleep(0.1)


    ##################################################################################
    def stop():
    ##################################################################################
        global _S
        if _S:
            _S.stop()

except ImportError:
    print("redys server not supported")
    async def start():
        pass
    def stop():
        pass
