# htagweb

[![Test](https://github.com/manatlan/htagweb/actions/workflows/on_commit_do_all_unittests.yml/badge.svg)](https://github.com/manatlan/htagweb/actions/workflows/on_commit_do_all_unittests.yml)

<a href="https://pypi.org/project/htagweb/">
    <img src="https://badge.fury.io/py/htagweb.svg?x" alt="Package version">
</a>

This "htagweb" module provides two htag's "runners":

 * WebServer     : for http only exchanges
 * WebServerWS   : for http/ws exchanges (first rendering is on http)

Theses runners are a lot more complete than the defaults ones (WebHTTP & WebWS, provided nativly with htag)
If you want to expose your HTag apps on the web : **they are the only real/official solutions**.
Theses are a lot robust and IRL tested.

 * based on [starlette](https://pypi.org/project/starlette/)
 * compatible with **uvloop** !!!
 * compatible with multiple gunicorn webworkers !!!
 * works on gnu/linux or windows !
 * Each user has its own process (for session, and htag app)
 * real starlette session available (in htag instance, and starlette request)
 * compatible with oauth2 authent ( [authlib](https://pypi.org/project/Authlib/) )
 * real process managments (interactions timeout, process expirations, ...)
 * **NOT READY YET** parano mode (can aes encrypt all communications between client & server ... to avoid mitm'proxies)

But be aware : it's production ready (at least, for me). It may not be free of bugs or security holes: USE AT YOUR OWN RISK.
Htag and this module are youngs, and not widely tested (by experts/hackers). But due to the nature of htag, and theses runners,
the risk may be minimal (only DoS), stealing datas may not be possible.

The concepts are the same :

 - one user can run only one instance of an htag app at one time (like in desktop mode).
 - All user processes are destroyed, after an inactivity timeout (not like in desktop mode, to preserve healthy of the webserver)
 - the "session" live as long as the server live (may not be a problem on many hosting service (where they shutdown the server after inactivities))

## architecture

Here is a rapid [map](https://www.tldraw.com/s/v2_c_0z8CUdwoKgrIjBa29yeO7?viewport=228%2C-15%2C1920%2C976&page=page%3AlnBx9GrxTdcdrdgOk-s83) ;-)

## Roadmap / futur

- ? replace starlette by fastapi ?
- better logging !!!!
- more parameters (session size, etc ...)
- parano mode
- perhaps a bi-modal version (use ws, and fallback to http when ws com error)


## Examples

A "hello world" could be :

```python
from htag import Tag

class App(Tag.div):
    def init(self):
        self+= "hello world"

from htagweb import WebServer # or WebServerWS
WebServer( App ).run()
```

or, with gunicorn (in a `server.py` file):

```python
from htag import Tag

class App(Tag.div):
    def init(self):
        self+= "hello world"

from htagweb import WebServer # or WebServerWS
app=WebServer( App )
```

and run server :

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornH11Worker -b localhost:8000 --preload server:app
```

See a more advanced example in [examples folder](https://github.com/manatlan/htagweb/tree/master/examples)

```bash
python3 examples/main.py
```
