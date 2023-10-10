# htagweb

[![Test](https://github.com/manatlan/htagweb/actions/workflows/on_commit_do_all_unittests.yml/badge.svg)](https://github.com/manatlan/htagweb/actions/workflows/on_commit_do_all_unittests.yml)

<a href="https://pypi.org/project/htagweb/">
    <img src="https://badge.fury.io/py/htagweb.svg?x" alt="Package version">
</a>

This module exposes htag's runners for the web. It's the official runners to expose
htag apps on the web, to handle multiple clients/session in the right way.

There are 3 runners:

 - **AppServer** : the real one ;-)
 - SimpleServer : for tests purposes
 - HtagServer : (use SimpleServer) to browse/expose python/htag files in an UI.

## AppServer

It's the real runner to expose htag apps in a real production environment, and provide
all features, while maintaining tag instances like classical/desktop htag runners.

All htag apps are runned in its own process, and an user can only have an instance of an htag app. (so process are recreated when query params changes)
Process live as long as the server live (TODO: a TIMEOUT will be back soon)

**Features**

 * based on [starlette](https://pypi.org/project/starlette/)
 * use sessions (multiple ways to handle sessions (file, mem, etc ...))
 * compatible with **uvloop** !!!
 * compatible with multiple gunicorn/uvicorn/webworkers !!!
 * compatible with [tag.update()](https://manatlan.github.io/htag/tag_update/)
 * works on gnu/linux, ios or windows (from py3.7 to py3.11)!
 * real starlette session available (in tag.state, and starlette request.session)
 * compatible with oauth2 authent ( [authlib](https://pypi.org/project/Authlib/) )
 * 'parano mode' (can aes encrypt all communications between client & server ... to avoid mitm'proxies on ws/http interactions)
 * auto reconnect websocket

### Instanciate

Like a classical starlette'app :

```python
from htagweb import AppServer
from yourcode import YourApp # <-- your htag class

app=AppServer( YourApp, ... )
if __name__=="__main__":
    app.run()
```

You can use the following parameters :

#### debug (bool)

- When False: (default) no debugging facilities
- When True: use starlette debugger.

#### ssl (bool)

- When False: (default) use "ws://" to connect the websocket
- When True: use "wss://" to connect the websocket

non-sense in http_only mode.

#### parano (bool)

- When False: (default) interactions between front/ui and back are in clear text (json), readable by a MITM.
- When True: interactions will be encrypted (less readable by a MITM, TODO: will try to use public/private keys in future)

this parameter is available on `app.handle(request, obj, ... parano=True|False ...)` too, to override defaults !

#### http_only (bool)

- When False: (default) it will use websocket interactions (between front/ui and back), with auto-reconnect feature.
- When True: it will use http interactions (between front/ui and back). But "tag.update" feature will not be available.

this parameter is available on `app.handle(request, obj, ... http_only=True|False ...)` too, to override defaults !

#### timeout_interaction (int)

It's the time (in seconds) for an interaction (or an initialization) for answering. If the timeout happens : the process/instance is killed.
By default, it's `60` seconds (1 minute).

#### timeout_inactivity (int)

It's the time (in seconds) of inactivities, after that : the process is detroyed.
By default, it's `0` (process lives as long as the server lives).

IMPORTANT : the "tag.update" feature doesn't reset the inactivity timeout !

#### session_factory (htagweb.sessions)

You can provide a Session Factory to handle the session in different modes.

- htagweb.sessions.MemDict (default) : sessions are stored in memory (renewed on reboot)
- htagweb.sessions.FileDict : sessions are stored in filesystem (renewed on reboot)
- htagweb.sessions.FilePersistentDict : make sessions persistent after reboot

## SimpleServer

It's a special runner for tests purposes. It doesn't provide all features (parano mode, ssl, session factory...).
Its main goal is to provide a simple runner during dev process, befause when you hit "F5" :
it will destroy/recreate the tag instances.

SimpleServer uses only websocket interactions (tag instances exist only during websocket connexions)

And it uses `htagweb.sessions.FileDict` as session manager.

## HtagServer

It's a special runner, which is mainly used by the `python3 -m htagweb`, to expose
current python/htag files in a browser. Its main goal is to test quickly the files
whose are in your folder, using an UI in your browser.

It uses the SimpleServer, so it does'nt provide all features (parano mode, ssl, session factory ...)

-------------------------------

## Roadmap / futur

 - make it works with gunicorn again !!!!!!!!!!!!!!!!!!!!!!!!!
 - better unittests !!!!!!!!!!!!!!!!
 - better logging !!!!!!!!!!!!!!!!
 - process lives : timeout !
 - parano mode : use public/private keys ?




## Examples

A "hello world" could be :

```python
from htag import Tag

class App(Tag.div):
    def init(self):
        self+= "hello world"

from htagweb import AppServer
AppServer( App ).run()
```

or, with gunicorn (in a `server.py` file, as following):

```python
from htag import Tag

class App(Tag.div):
    def init(self):
        self+= "hello world"

from htagweb import AppServer
app=AppServer( App )
```

and run server :

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornH11Worker -b localhost:8000 --preload server:app
```

See a more advanced example in [examples folder](https://github.com/manatlan/htagweb/tree/master/examples)

```bash
python3 examples/main.py
```

# Standalone module can act as server

The module can act as "development server", providing a way to quickly run any htag class in a browser. And let you browse current `*.py` files in a browser.

```bash
$ python3 -m htagweb
```
htagweb will look for an "index:App" (a file `index.py` (wich contains a htag.Tag subclass 'App').), and if it can't found it : expose its own htag app to let user browse pythons files in the browser (`/!\`)

or

```bash
$ python3 -m htagweb main:App
```
if you want to point the "/" (home path) to a file `main.py` (wich contains a htag.Tag subclass 'App').

