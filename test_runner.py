import pytest
from htag import Tag
from htagweb import Runner
import sys,json
from starlette.testclient import TestClient
from starlette.responses import PlainTextResponse

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


def test_runner_route_static():

    def do_tests(client):
        # assert nothing is at "/"
        response = client.get('/')
        assert response.status_code == 404

        # but something is at "/hello"
        response = client.get('/hello')
        assert response.status_code == 200
        assert response.text == "world"


    async def serve(req): return PlainTextResponse("world")

    app=Runner()
    app.add_route("/hello", serve)
    with TestClient(app) as client:
        do_tests(client)


def test_runner_route_app():

    def do_tests(client):
        # assert nothing is at "/"
        response = client.get('/')
        assert response.status_code == 404

        # but something is at "/hello"
        response = client.get('/an_app')
        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text

    async def serve_an_app(req):
        return await req.app.handle(req,"examples.simple.App") 

    app=Runner()
    app.add_route("/an_app", serve_an_app)
    with TestClient(app) as client:
        do_tests(client)        