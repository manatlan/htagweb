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
from datetime import datetime

class Fifo:
    # FOLDER="./ses"
    FOLDER="/tmp"
    def __init__(self,uid:str,moduleapp:str):
        self.uid=uid
        self.moduleapp=moduleapp
        
        self.CLIENT_TO_SERVER_FIFO = f'{Fifo.FOLDER}/{uid}/{moduleapp}/in'
        self.SERVER_TO_CLIENT_FIFO = f'{Fifo.FOLDER}/{uid}/{moduleapp}/out'
        self.UPDATE_FIFO = f'{Fifo.FOLDER}/{uid}/{moduleapp}/update'
        self.PID_FILE = f'{Fifo.FOLDER}/{uid}/{moduleapp}/PID'
    
    def __str__(self):
        # minimize uid (to be clearer in log output)
        return f'{self.uid[:2]}~{self.uid[-2:]}.{self.moduleapp}'

    def exists(self) -> bool:
        return os.path.exists(self.CLIENT_TO_SERVER_FIFO) and os.path.exists(self.SERVER_TO_CLIENT_FIFO)

    def dates(self) -> tuple:
        if self.exists():
            stat = os.stat(self.PID_FILE)
            cdate = datetime.fromtimestamp(stat.st_ctime)
            stat = os.stat(self.CLIENT_TO_SERVER_FIFO)
            mdate = datetime.fromtimestamp(stat.st_mtime)
            return (cdate,mdate)
        else:
            return (None,None)

    def createPipes(self):  # for server
        # Créer les named pipes
        folder = os.path.dirname(self.CLIENT_TO_SERVER_FIFO)
        if not os.path.isdir(folder):
            os.makedirs(folder)

        if not os.path.exists(self.CLIENT_TO_SERVER_FIFO):
            os.mkfifo(self.CLIENT_TO_SERVER_FIFO)
            os.chmod(self.CLIENT_TO_SERVER_FIFO, 0o700)
        if not os.path.exists(self.SERVER_TO_CLIENT_FIFO):
            os.mkfifo(self.SERVER_TO_CLIENT_FIFO)
            os.chmod(self.SERVER_TO_CLIENT_FIFO, 0o700)

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
        if os.path.isdir(folder):
            os.removedirs(folder)   

    async def com(self,command:str,**args) -> "str|dict":  # for client only
        async with aiofiles.open(self.CLIENT_TO_SERVER_FIFO, mode='w') as fifo_out, aiofiles.open(self.SERVER_TO_CLIENT_FIFO, mode='r') as fifo_in:
            args["cmd"]=command
            # print("Client send:",args)
            await fifo_out.write(json.dumps(args) + '\n')
            await fifo_out.flush()

            # Lire la réponse du process serveur
            frame = await fifo_in.readline()

            #print("Client receive:",frame)
            try:
                c = json.loads(frame.strip())
            except json.decoder.JSONDecodeError as e:
                raise Exception(f"fifo com json error '{e}' : >>>{frame.strip()}<<<")
            if "err" in c:
                raise Exception(f"hrprocess error : {c['err']}")
            return c["response"]


    @staticmethod
    def childs():
        for i in glob.glob(Fifo.FOLDER+"/*/*/PID"):
            fs=i.split("/")
            uid = fs[-3]
            moduleapp = fs[-2]
            yield Fifo(uid,moduleapp)

    def destroy(self):
        if os.path.isfile(self.PID_FILE):
            with open(self.PID_FILE,"r+") as fid:
                try:
                    os.kill(int(fid.readline().strip()),9)
                except ProcessLookupError:
                    pass
        self.removePipes()
