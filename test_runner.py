import pytest
from htag import Tag
from htagweb import Runner
import sys,json
from starlette.testclient import TestClient

import bs4

def test_runner_ws_mode():

    def do_tests(client):
        response = client.get('/')

        # assert that get bootstrap page
        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text


        soup=bs4.BeautifulSoup(response.text,"html.parser")
        id=soup.select("button")[-1].get("id")
        datas={"id":int(id),"method":"__on__","args":["onclick-"+str(id)],"kargs":{},"event":{}}

        with client.websocket_connect('/_/examples.simple.App') as websocket:

            #following exchanges will be json <-> json
            websocket.send_text( json.dumps(datas) )

            dico = json.loads(websocket.receive_text())
            assert "update" in dico

    app=Runner("examples.simple.App")
    with TestClient(app) as client:
        do_tests(client)

