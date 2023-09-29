# htagweb

[![Test](https://github.com/manatlan/htagweb/actions/workflows/on_commit_do_all_unittests.yml/badge.svg)](https://github.com/manatlan/htagweb/actions/workflows/on_commit_do_all_unittests.yml)

<a href="https://pypi.org/project/htagweb/">
    <img src="https://badge.fury.io/py/htagweb.svg?x" alt="Package version">
</a>

This "htagweb" module is the official way to expose htag's apps on the web.

**ULTRA IMPORTANT** ;-)

**This module will be completly rewritten (for the 3rd time ;-)). And it will work, like in the past, as others classicals runners (tag instances will live, in separates processes). (state and session will remain too). Just need to test the new branch (it will use redys ;-) )**

**Important note**
On the web, the server can handle many clients : so, it's not possible to handle each tag instances per user. SO there are 1 limitation compared to classical htag runners which comes with htag.

 - ~~there can be only one managed instance of a htag class, per user~~ (it's the case in classical runners too)
 - and tag instances doesn't live as long as the runner lives (when you hit F5, it will be destroyed/recreated). So, keeping states must be done thru the tag.state / tag.root.state (which is the session of the user).

So developping a htag app which work the same on desktop and on the web, should manage its states in tag.state / tag.root.state ;-)

 ## Features

 * based on [starlette](https://pypi.org/project/starlette/)
 * multiple ways to handle sessions (file, mem, etc ...)
 * compatible with **uvloop** !!!
 * compatible with multiple gunicorn/uvicorn/webworkers !!!
 * compatible with [tag.update()](https://manatlan.github.io/htag/tag_update/)
 * works on gnu/linux, ios or windows !
 * real starlette session available (in tag.state, and starlette request.session)
 * compatible with oauth2 authent ( [authlib](https://pypi.org/project/Authlib/) )
 * 'parano mode' (can aes encrypt all communications between client & server ... to avoid mitm'proxies on ws exchanges)

## Roadmap / futur

priority :

 - ci/cd test python>3.7 with shared_memory_dict
 - unittests on sessions.memory (won't work now)
 - better unittests on usot

futur:

 - ? replace starlette by fastapi ?
 - the double rendering (double init creation) is not ideal. But great for SEO bots. Perhaps I could find a better way (and let only one rendering, but how ?!) ?!
 - more unittests !!!
 - better logging !!!


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

