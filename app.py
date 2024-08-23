from flask import Flask, redirect, request, session
from spogitify import *
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify
import time
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config.update(get_config())

# Helper functions

def setup_app():
    config = get_config()
    for k in ['spotify_client_id', 'spotify_client_secret', 'spotify_redirect_uri']:
        if not config[k]:
            raise ValueError(f"{k} must be set in config.yaml")
        app.config[k] = config[k]

def spotify_oauth():
    return SpotifyOAuth(
        client_id=app.config['spotify_client_id'],
        client_secret=app.config['spotify_client_secret'],
        redirect_uri=app.config['spotify_redirect_uri'],
        scope='user-library-read playlist-read-private',
        cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session),
        state=str(uuid.uuid4())
    )

def spotify():
    sp_oauth = spotify_oauth()
    if not sp_oauth.validate_token(sp_oauth.get_cached_token()):
        return None
    auth_token = sp_oauth.get_cached_token()['access_token']
    return Spotify(auth=auth_token)

def login_redirect():
    session['previous_page'] = request.url
    auth_url = spotify_oauth().get_authorize_url()
    return redirect(auth_url)

# Routes

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "healthy"}, 200

@app.route('/authorize')
def authorize():
    spotify_oauth().get_access_token(request.args['code'])
    sp = spotify()
    if sp:
        user_info = sp.me()
        session['user_id'] = user_info['id']
        return redirect(session.pop('previous_page', '/'))
    return {"error": "Failed to get access token"}, 400

@app.route('/')
def whoami():
    sp = spotify()
    if not sp:
        return login_redirect()
    user_info = sp.me()
    return {
        'name': user_info['display_name'],
        'id': user_info['id']
    }, 200

if __name__ == '__main__':
    setup_app()
    app.run(debug=True)
