import os,sys; sys.path.insert(0,os.path.realpath(os.path.dirname(os.path.dirname(__file__))))

from htag import Tag
from htagweb import Runner
from authlib.integrations.starlette_client import OAuth
from starlette.responses import Response,RedirectResponse
import time

##################################################################################################
## !!! important things to adapt to your needs !!!
##################################################################################################
CLIENT_ID='xxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com'
CLIENT_SECRET='GOXXXX-xxxxxxxxxxxxxxxxxxxxxxxxxxxx'
REDIRECT_URI = "http://localhost:8000/oauth_auth"                       #<= should be declared in your console !!!
##################################################################################################

OAUTH_SESSION_NAME = "User" # name of the var in session for holding the userinfo/oauth/google

OAUTH = OAuth()
OAUTH.register(
    name='google',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'select_account',  # force to select account
    }
)

async def oauth_request_action(request):
    """ an unique entrypoint for all google/oauth actions"""
    action=request.path_params.get("action")
    current_url=request.headers.get('REFERER','/')
    if action == "login":
        request.session["REFERER"]=current_url
        redirect_uri = REDIRECT_URI
        return await OAUTH.google.authorize_redirect(request, redirect_uri)
    elif action == "auth":
        token = await OAUTH.google.authorize_access_token(request)
        request.session[OAUTH_SESSION_NAME]=token.get('userinfo')
        return RedirectResponse(url=request.session["REFERER"])
    elif action == "logout":
        del request.session[OAUTH_SESSION_NAME]
        return RedirectResponse(url=current_url)
    else:
        return Response(f'not found',404)


class TagOAuth(Tag.span):
    def init(self,state):
        self["class"]="TagOAuth"
        self._rootstate = state
        self.title=Tag.span()
        self.btn = Tag.button(_onclick=self.onclick)

    @property
    def user(self): # -> dict or empty dict
        """ just expose a property to easily access to the user from session """
        return self._rootstate.get(OAUTH_SESSION_NAME,{})

    def render(self): # dynamic rendering
        self.clear()
        self+= self.title + self.btn
        if self.user:
            self.title.set(self.user['name'])
            self.btn.set("SignOut")
        else:
            self.title.set("")
            self.btn.set("SignIn")

    def onclick(self,o:Tag.button):
        if self.user:
            self.call( "document.location.href='/oauth_logout'")
        else:
            self.call( "document.location.href='/oauth_login'")


class App(Tag.body):
    statics="""
        .TagOAuth {float:right;border:1px solid black;border-radius:10px;padding:10px}
    """
    def init(self):
        self.oa = TagOAuth(self.state)

    def render(self):  # dynamic rendering
        self.clear()

        self += self.oa
        self += f"You are {self.oa.user.get('name') or 'unknown'}"

#=========================================

# IT WORKS FOR THE 3 runners of htagweb ;-) (should work with old webhttp/webws runners from htag too)
app=Runner(App)

app.add_route("/oauth_{action}", oauth_request_action )

if __name__=="__main__":
    import logging
    logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.DEBUG)

    app.run(openBrowser=True)



