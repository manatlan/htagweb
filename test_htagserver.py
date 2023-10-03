import pytest
from htag import Tag
from htagweb import HtagServer,SimpleServer
import sys,json
from starlette.testclient import TestClient

def test_HtagServer_index():
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

            # here is the IndexApp browser


def test_HtagServer_instanciates_htagapps():

    def do_tests():
        # assert that get bootstrap page
        assert response.status_code == 200
        assert "document.write(html)" in response.text

        with client.websocket_connect('/_/test_hr.App') as websocket:

            # assert 1st connect send back the full html page
            html = websocket.receive_text()
            assert html.startswith("<!DOCTYPE html>")

            #following exchanges will be json <-> json
            msg=dict(id="ut",method="doit",args=(),kargs={})
            websocket.send_text( json.dumps(msg) )

            dico = json.loads(websocket.receive_text())
            assert "update" in dico

    app=HtagServer()
    with TestClient(app) as client:
        response = client.get('/test_hr.App')
        do_tests()
        response = client.get('/test_hr:App')
        do_tests()
        response = client.get('/test_hr')
        do_tests()


def test_simpleserver():
    app=SimpleServer( "test_hr:App" )
    with TestClient(app) as client:
        response = client.get('/')

        # assert that get bootstrap page
        assert response.status_code == 200
        assert "document.write(html)" in response.text

        with client.websocket_connect('/_/test_hr.App') as websocket:

            # assert 1st connect send back the full html page
            html = websocket.receive_text()
            assert html.startswith("<!DOCTYPE html>")

            # #following exchanges will be json <-> json
            msg=dict(id="ut",method="doit",args=(),kargs={})
            websocket.send_text( json.dumps(msg) )

            dico = json.loads(websocket.receive_text())
            assert "update" in dico




if __name__=="__main__":
    # test_basic()
    # test_a_full_fqn()
    test_simpleserver()