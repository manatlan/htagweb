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
from datetime import datetime
import socket
import tempfile
from asyncio import LimitOverrunError

class AsyncStream:
    # FOLDER="./ses"
    FOLDER="/tmp"
    
    def __init__(self, uid: str, moduleapp: str):
        self.uid = uid
        self.moduleapp = moduleapp
        
        # Chemins pour les sockets Unix (remplace les FIFOs)
        self.CLIENT_TO_SERVER_SOCKET = f'{AsyncStream.FOLDER}/{uid}/{moduleapp}/in.sock'
        self.SERVER_TO_CLIENT_SOCKET = f'{AsyncStream.FOLDER}/{uid}/{moduleapp}/out.sock'
        self.UPDATE_SOCKET = f'{AsyncStream.FOLDER}/{uid}/{moduleapp}/update.sock'
        self.PID_FILE = f'{AsyncStream.FOLDER}/{uid}/{moduleapp}/PID'
        
        # Pour la compatibilité avec l'ancien code
        self.CLIENT_TO_SERVER_FIFO = self.CLIENT_TO_SERVER_SOCKET
        self.SERVER_TO_CLIENT_FIFO = self.SERVER_TO_CLIENT_SOCKET
        self.UPDATE_FIFO = self.UPDATE_SOCKET

    def __str__(self):
        # minimize uid (to be clearer in log output)
        return f'{self.uid[:2]}~{self.uid[-2:]}.{self.moduleapp}'

    def exists(self) -> bool:
        return os.path.exists(self.CLIENT_TO_SERVER_SOCKET)

    def dates(self) -> tuple:
        if self.exists():
            stat = os.stat(self.PID_FILE)
            cdate = datetime.fromtimestamp(stat.st_ctime)
            stat = os.stat(self.CLIENT_TO_SERVER_SOCKET)
            mdate = datetime.fromtimestamp(stat.st_mtime)
            return (cdate, mdate)
        else:
            return (None, None)

    def createPipes(self):  # for server
        # Créer le répertoire
        folder = os.path.dirname(self.CLIENT_TO_SERVER_SOCKET)
        if not os.path.isdir(folder):
            os.makedirs(folder)

    def removePipes(self):  # for server
        # Supprimer les sockets et fichiers
        for sock_file in [self.CLIENT_TO_SERVER_SOCKET, self.SERVER_TO_CLIENT_SOCKET, self.UPDATE_SOCKET]:
            if os.path.exists(sock_file):
                try:
                    os.remove(sock_file)
                except OSError:
                    pass
        
        if os.path.isfile(self.PID_FILE):
            os.unlink(self.PID_FILE)

        folder = os.path.dirname(self.SERVER_TO_CLIENT_SOCKET)
        if os.path.isdir(folder):
            try:
                os.removedirs(folder)
            except OSError:
                pass

    async def com(self, command: str, **args) -> "str|dict":  # for client only
        try:
            # Connexion au serveur via socket Unix avec une limite augmentée
            # La limite par défaut est 64Ko, on passe à 10Mo pour gérer les très gros échanges de données
            # et éviter les erreurs "Separator is found, but chunk is longer than limit"
            reader, writer = await asyncio.open_unix_connection(
                self.CLIENT_TO_SERVER_SOCKET,
                limit=10*1024*1024  # 10Mo
            )
            
            args["cmd"] = command
            # Envoyer la commande
            writer.write((json.dumps(args) + '\n').encode())
            await writer.drain()

            # Lire la réponse
            try:
                data = await reader.readline()
                if not data:
                    raise Exception("Connection closed by server")
            except asyncio.LimitOverrunError as e:
                raise Exception(f"Message too large (limit: 10Mo). Consider optimizing data size or increasing limit: {e}")
            
            frame = data.decode().strip()
            try:
                c = json.loads(frame)
            except json.decoder.JSONDecodeError as e:
                raise Exception(f"async_stream com json error '{e}' : >>>{frame}<<<")
            
            if "err" in c:
                raise Exception(f"hrprocess error : {c['err']}")
            
            writer.close()
            await writer.wait_closed()
            return c["response"]
            
        except (ConnectionRefusedError, FileNotFoundError) as e:
            raise Exception(f"Cannot connect to server: {e}")

    @staticmethod
    def childs():
        for i in glob.glob(AsyncStream.FOLDER + "/*/*/PID"):
            fs = i.split("/")
            uid = fs[-3]
            moduleapp = fs[-2]
            yield AsyncStream(uid, moduleapp)

    def destroy(self):
        if os.path.isfile(self.PID_FILE):
            with open(self.PID_FILE, "r+") as fid:
                try:
                    os.kill(int(fid.readline().strip()), 9)
                except ProcessLookupError:
                    pass
        self.removePipes()


