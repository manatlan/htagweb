# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2024 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################
import glob
from .fifo import Fifo
from .session import Session

class HApp:
    def __init__( self, uid:str,moduleapp:str,pid:int ):
        self.fifo=Fifo(uid,moduleapp)
        self.cdate,self.mdate = self.fifo.dates()
        self.pid=pid

    def kill(self):
        self.fifo.removePipes()
        #TODO: if it's the last app -> should kill the session, to be clean ;-)

    def __str__(self):
        return f"{self.fifo.moduleapp} (pid:{self.pid})"

class HUser:
    def __init__(self,uid:str,apps:list):
        self.uid=uid
        self._apps=apps
    
    @property
    def apps(self):
        return self._apps

    @property
    def session(self):
        return dict(Session(self.uid))

    def kill(self):
        for app in self._apps:
            app.kill()
        Session(self.uid).clear()

    def __str__(self):
        return f"{self.uid}"

def users() -> list:
    u={}
    for i in glob.glob(Fifo.FOLDER+"/*/*/PID"):
        pid = int(open(i,"r+").read())
        fs=i.split("/")
        uid = fs[-3]
        moduleapp = fs[-2]

        u.setdefault(uid,[]).append( HApp(uid,moduleapp,pid) )

    ll=[]
    for uid,apps in u.items():
        ll.append( HUser(uid,apps) )
    return ll