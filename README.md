# htagweb

## NOT READY

## NOT READY

## NOT READY

## NOT READY


This "htagweb" module provides two htag's "runners":

 * WebServer     : for http only exchanges
 * WebServerWS   ! for http/ws exchanges (first rendering is on http)

Theses runners are a lot more complete than the defaults ones (WebHTTP & WebWS, provided nativly with htag)
If you want to expose your HTag apps on the web : **they are the only real/official solutions**.
Theses are a lot robust and IRL tested.

 * based on [starlette](https://pypi.org/project/starlette/)
 * each htag app is runned in its own process, per user (real isolation!)
 * real starlette session available (in htag instance, and starlette request)
 * compatible with oauth2 authents ( [authlib](https://pypi.org/project/Authlib/) )
 * works with multiple uvicorn/gunicorn webworkers
 * real process managments (interactions timeout, process expirations, ...)
 * **NOT READY YET** parano mode (can aes encrypt all communications between client & server ... to avoid mitm'proxies)

But be aware : it's production ready (at least, for me). It may not be free of bugs or security holes: USE AT YOUR OWN RISK.
Htag and this module are youngs, and not widely tested (by experts/hackers). But due to the nature of htag, and theses runners,
the risk may be minimal (only DoS), stealing datas may not be possible.

The concepts are the same :

 - one user can run only one instance(process) of an htag app at one time (like in desktop mode).
 - All user's instances(process) are destroyed, after an inactivity timeout (not like in desktop mode, to preserve healthy of the webserver)
 - the "session" live as long as the server live (may not be a problem on many hosting service (where they shutdown the server after inactivities))


----

A "hello world" could be :

```python

from htag import Tag

class App(Tag.div):
    def init(self):
        self+= "hello world"

from htagweb import WebServer # or WebServerWS
WebServer( App ).run()
```

See more in "examples" folder
