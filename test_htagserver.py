import pytest
from htag import Tag
from htagweb import HtagServer
import sys,json
from starlette.testclient import TestClient

def test_basic():
    app=HtagServer()
    with TestClient(app) as client:
        response = client.get('/')

        # assert that get bootstrap page
        assert response.status_code == 200
        assert "document.write(html)" in response.text

        print(response.text)

        with client.websocket_connect('/_/htagweb.htagserver.IndexApp') as websocket:

            # assert 1st connect send back the full html page
            html = websocket.receive_text()
            assert html.startswith("<!DOCTYPE html>")

            #TODO: continue here


def test_a_full_fqn():
    app=HtagServer()
    with TestClient(app) as client:
        response = client.get('/test_hr.App')

        # assert that get bootstrap page
        assert response.status_code == 200
        assert "document.write(html)" in response.text

        with client.websocket_connect('/_/test_hr.App') as websocket:

            # assert 1st connect send back the full html page
            html = websocket.receive_text()
            assert html.startswith("<!DOCTYPE html>")

            #TODO: continue here
            # following exchanges will be json <-> json
            # msg=dict(id="ut",method="doit",args=(),kargs={})
            # websocket.send_text( json.dumps(msg) )

            # dico = json.loads(websocket.receive_text())
            # assert "update" in dico


def test_a_light_fqn():
    app=HtagServer()
    with TestClient(app) as client:
        response = client.get('/test_hr')

        # assert that get bootstrap page
        assert response.status_code == 200
        assert "document.write(html)" in response.text

        with client.websocket_connect('/_/test_hr.App') as websocket:

            # assert 1st connect send back the full html page
            html = websocket.receive_text()
            assert html.startswith("<!DOCTYPE html>")

            #TODO: continue here

def test_parano():
    app=HtagServer(parano=True)
    with TestClient(app) as client:
        response = client.get('/')

        # assert that get bootstrap page
        assert response.status_code == 200
        assert "document.write(html)" in response.text
        assert "_PARANO_" in response.text
        assert "encrypt" in response.text

        # the rest will be encrypted ;-)

if __name__=="__main__":
    test_basic()
    test_a_full_fqn()