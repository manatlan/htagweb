# htagweb

[![Test](https://github.com/manatlan/htagweb/actions/workflows/on_commit_do_all_unittests.yml/badge.svg)](https://github.com/manatlan/htagweb/actions/workflows/on_commit_do_all_unittests.yml)

<a href="https://pypi.org/project/htagweb/">
    <img src="https://badge.fury.io/py/htagweb.svg?x" alt="Package version">
</a>

This "htagweb" module is the official way to expose htag's apps on the web

 ## Features

 * based on [starlette](https://pypi.org/project/starlette/)
 * compatible with **uvloop** !!!
 * compatible with multiple gunicorn/uvicorn/webworkers !!!
 * works on gnu/linux or windows !
 * real starlette session available (in htag instance, and starlette request)
 * compatible with oauth2 authent ( [authlib](https://pypi.org/project/Authlib/) )
 * 'parano mode' (can aes encrypt all communications between client & server ... to avoid mitm'proxies)

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

from htagweb import AppServer
AppServer( App ).run()
```

or, with gunicorn (in a `server.py` file):

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

TODO: complete here !

```bash
$ python3 -m htagweb
```
htagweb will look for an "index:App" (a file `index.py` (wich contains a htag.Tag subclass 'App').), and if it can't found it : expose its own htag app to let user browse pythons files in the browser (`/!\`)

or

```bash
$ python3 -m htagweb main:App
```
if you want to point the "/" (home path) to a file `main.py` (wich contains a htag.Tag subclass 'App').

