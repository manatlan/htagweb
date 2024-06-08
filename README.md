# htagweb 
[![Test](https://github.com/manatlan/htagweb/actions/workflows/on_commit_do_all_unittests.yml/badge.svg)](https://github.com/manatlan/htagweb/actions/workflows/on_commit_do_all_unittests.yml)

<a href="https://pypi.org/project/htagweb/">
    <img src="https://badge.fury.io/py/htagweb.svg?x" alt="Package version">
</a>

This module exposes htag's runners for the web. It's the official runners to expose
htag apps on the web, to handle multiple clients/session in the right way.


## Runner

It's the real runner to expose htag apps in a real production environment, and provide
all features, while maintaining tag instances like classical/desktop htag runners.

All htag apps are runned in its own process, and an user can only have an instance of an htag app. (so process are recreated when query params changes)
Process live as long as the server live

**Features**

 * based on [starlette](https://pypi.org/project/starlette/)
 * use session
 * compatible with **uvloop** !!!
 * compatible with multiple gunicorn/uvicorn/webworkers !!!
 * compatible with [tag.update()](https://manatlan.github.io/htag/tag_update/)
 * works on gnu/linux, ios ~~or windows~~ (from py3.8 to py3.11)! (**not py3.7 anymore ;-(**)
 * real starlette session available (in tag.state, and starlette request.session)
 * compatible with oauth2 authent ( [authlib](https://pypi.org/project/Authlib/) )
 * 'parano mode' (can aes encrypt all communications between client & server ... to avoid mitm'proxies on ws/http interactions)
 * auto reconnect websocket

### Instanciate

Like a classical starlette'app :

```python
from htagweb import Runner
from yourcode import YourApp # <-- your htag class

app=Runner( YourApp, ... )
if __name__=="__main__":
    app.run()
```

You can use the following parameters :

#### host (str)

The host to bind to. (default is "0.0.0.0")

#### port (int)

The port to bind to. (default is 8000)

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


### to add an endpoint (add_route)

Example to add a static endpoint :

```python
from starlette.responses import PlainTextResponse

async def serve(req):
    return PlainTextResponse("body {}")

app=Runner( App, debug=False, ssl=True )
app.add_route("/my.css", serve)
```

Example to add another htag app on another endpoint :

```python
async def serve(req):
    return await req.app.handle(req, App2 )

app=Runner( App, debug=False, ssl=True )
app.add_route("/my_other_app", serve)
```


-------------------------------

## Roadmap / futur

 - more unittests !!!!!!!!!!!!!!!!
 - better logging !!!!!!!!!!!!!!!!
 - parano mode : use public/private keys ?


## Examples

A "hello world" could be :

```python
from htag import Tag

class App(Tag.div):
    def init(self):
        self<= "hello world"

from htagweb import Runner
Runner( App ).run()
```

or, with gunicorn (in a `server.py` file, as following):

```python
from htag import Tag

class App(Tag.div):
    def init(self):
        self<= "hello world"

from htagweb import Runner
app=Runner( App )
```

and run server :

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornH11Worker -b localhost:8000 --preload server:app
```

See a more advanced example in [examples folder](https://github.com/manatlan/htagweb/tree/master/examples)

```bash
python3 examples/main.py
```


