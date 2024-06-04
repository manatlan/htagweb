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


        id=bs4.BeautifulSoup(response.text,"html.parser").select("button")[-1].get("id")
        datas={"id":int(id),"method":"__on__","args":["onclick-"+str(id)],"kargs":{},"event":{}}

        with client.websocket_connect('/_/examples.simple.App') as websocket:

            #following exchanges will be json <-> json
            websocket.send_text( json.dumps(datas) )

            dico = json.loads(websocket.receive_text())
            assert "update" in dico

    app=Runner("examples.simple.App")
    with TestClient(app) as client:
        do_tests(client)


def test_runner_http_mode():

    def do_tests(client):
        response = client.get('/')

        # assert that get bootstrap page
        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text

        id=bs4.BeautifulSoup(response.text,"html.parser").select("button")[-1].get("id")
        datas={"id":int(id),"method":"__on__","args":["onclick-"+str(id)],"kargs":{},"event":{}}

        response = client.post('/_/examples.simple.App',content=json.dumps(datas))
        dico = json.loads(response.text)
        assert "update" in dico

    app=Runner("examples.simple.App",http_only=True)
    with TestClient(app) as client:
        do_tests(client)
