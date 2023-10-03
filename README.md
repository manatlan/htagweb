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
 * multiple ways to handle sessions (file, mem, etc ...)
 * compatible with **uvloop** !!!
 * compatible with multiple gunicorn/uvicorn/webworkers !!!
 * compatible with [tag.update()](https://manatlan.github.io/htag/tag_update/)
 * works on gnu/linux, ios or windows !
 * real starlette session available (in tag.state, and starlette request.session)
 * compatible with oauth2 authent ( [authlib](https://pypi.org/project/Authlib/) )
 * 'parano mode' (can aes encrypt all communications between client & server ... to avoid mitm'proxies on ws exchanges)
 * auto reconnect websocket


#### debug (bool)

When False: (default) no debugging facilities
When True: use starlette debugger.

#### ssl (bool)

When False: (default) use "ws://" to connect the websocket
When True: use "wss://" to connect the websocket

non-sense in http_only mode.

#### parano (bool)

When False: (default) exchanges between front/ui and back are in clear text (json), readable by a MITM.
When True: exchanges will be encrypted (less readable by a MITM, TODO: will try to use public/private keys in future)

#### http_only(bool)

When False: (default) it will use websocket transport (between front/ui and back), with auto-reconnect feature.
When True: it will use http transport (between front/ui and back). But "tag.update" feature will not be available.

#### sesprovider (htagweb.sessions)

You can provide a Session Factory to handle the session in different modes.

- htagweb.sessions.MemDict (default) : sessions are stored in memory (renewed on reboot)
- htagweb.sessions.FileDict : sessions are stored in filesystem (renewed on reboot)
- htagweb.sessions.FilePersistentDict : make sessions persistent during reboot

## SimpleServer

It's a special runner for tests purposes. It doesn't provide all features (parano mode, ssl, session factory...).
Its main goal is to provide a simple runner during dev process, befause when you hit "F5" :
it will destroy/recreate the tag instances.

SimpleServer uses only websocket transport (tag instances exist only during websocket connexions)

And it uses `htagweb.sessions.FileDict` as session manager.

## HtagServer

It's a special runner, which is mainly used by the `python3 -m htagweb`, to expose
current python/htag files in a browser. Its main goal is to test quickly the files
whose are in your folder, using an UI in your browser.

It uses the SimpleServer, so it does'nt provide all features (parano mode, ssl, session factory ...)

-------------------------------

## Roadmap / futur

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

