# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2024 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################
import asyncio
import os
import json
import glob 
import aiofiles

class Fifo:
    # FOLDER="./ses"
    FOLDER="/tmp"
    def __init__(self,uid:str,moduleapp:str,timeout_interaction:int):
        self.uid=uid
        self.moduleapp=moduleapp
        self.timeout_interaction=timeout_interaction    # in seconds
        
        self.CLIENT_TO_SERVER_FIFO = f'{Fifo.FOLDER}/{uid}/{moduleapp}/in'
        self.SERVER_TO_CLIENT_FIFO = f'{Fifo.FOLDER}/{uid}/{moduleapp}/out'
        self.UPDATE_FIFO = f'{Fifo.FOLDER}/{uid}/{moduleapp}/update'
        self.PID_FILE = f'{Fifo.FOLDER}/{uid}/{moduleapp}/PID'
    
    def __str__(self):
        return f'{self.uid}.{self.moduleapp}'

    def exists(self) -> bool:
        return os.path.exists(self.CLIENT_TO_SERVER_FIFO) and os.path.exists(self.SERVER_TO_CLIENT_FIFO)

    def createPipes(self):  # for server
        # Créer les named pipes
        folder = os.path.dirname(self.CLIENT_TO_SERVER_FIFO)
        if not os.path.isdir(folder):
            os.makedirs(folder)

        if not os.path.exists(self.CLIENT_TO_SERVER_FIFO):
            os.mkfifo(self.CLIENT_TO_SERVER_FIFO)
        if not os.path.exists(self.SERVER_TO_CLIENT_FIFO):
            os.mkfifo(self.SERVER_TO_CLIENT_FIFO)
        if not os.path.exists(self.UPDATE_FIFO):
            os.mkfifo(self.UPDATE_FIFO)

    def removePipes(self):  # for server
        if os.path.exists(self.CLIENT_TO_SERVER_FIFO):
            os.remove(self.CLIENT_TO_SERVER_FIFO)
        if os.path.exists(self.SERVER_TO_CLIENT_FIFO):
            os.remove(self.SERVER_TO_CLIENT_FIFO)
        if os.path.exists(self.UPDATE_FIFO):
            os.remove(self.UPDATE_FIFO)

        if os.path.isfile(self.PID_FILE):
            os.unlink(self.PID_FILE)

        folder = os.path.dirname(self.SERVER_TO_CLIENT_FIFO)
        os.removedirs(folder)

    async def com(self,command:str,**args) -> "str|dict":  # for client only
        async with aiofiles.open(self.CLIENT_TO_SERVER_FIFO, mode='w') as fifo_out, aiofiles.open(self.SERVER_TO_CLIENT_FIFO, mode='r') as fifo_in:
            args["cmd"]=command
            # print("Client send:",args)
            await fifo_out.write(json.dumps(args) + '\n')
            await fifo_out.flush()

            # Lire la réponse du process serveur
            frame = await asyncio.wait_for(fifo_in.readline(), timeout=self.timeout_interaction)
            if frame is None:
                raise Exception(f"Timeout response (>{self.timeout_interaction})")

            #print("Client receive:",frame)
            c = json.loads(frame.strip())
            return c["response"]


    @staticmethod
    def childs():
        for i in glob.glob(Fifo.FOLDER+"/*/*/PID"):
            fs=i.split("/")
            uid = fs[-3]
            moduleapp = fs[-2]
            yield Fifo(uid,moduleapp,60)

    def destroy(self):
        with open(self.PID_FILE,"r+") as fid:
            try:
                os.kill(int(fid.readline().strip()),9)
            except ProcessLookupError:
                pass
        self.removePipes()