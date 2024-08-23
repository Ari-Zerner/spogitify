from flask import Flask, redirect, request, session
from spogitify import *
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify
import time
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config.update(get_config())

def sp_oauth():
    return SpotifyOAuth(
        client_id=app.config['spotify_client_id'],
        client_secret=app.config['spotify_client_secret'],
        redirect_uri=app.config['spotify_redirect_uri'],
        scope='user-library-read playlist-read-private',
        cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session),
        state=str(uuid.uuid4())
    )

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "healthy"}, 200

@app.route('/login')
def login():
    auth_url = sp_oauth().get_authorize_url()
    return redirect(auth_url)

@app.route('/authorize')
def authorize():
    token_info = sp_oauth().get_access_token(request.args['code'])
    if token_info:
        token_info['expires_at'] = token_info['expires_in'] + int(time.time())
        session['token_info'] = token_info
        sp = Spotify(auth=token_info['access_token'])
        user_info = sp.me()
        session['user_id'] = user_info['id']
        return redirect('/')
    return {"error": "Failed to get access token"}, 400

def get_token():
    token_info = session.get('token_info', None)
    if not token_info:
        return None

    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60 # 1 minute buffer

    if is_expired:
        token_info = sp_oauth().refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info

    return token_info['access_token']

@app.route('/')
def whoami():
    access_token = get_token()
    if not access_token:
        return redirect('/login')
    
    sp = Spotify(auth=access_token)
    user_info = sp.me()
    
    return {
        'name': user_info['display_name'],
        'id': user_info['id']
    }, 200

if __name__ == '__main__':
    app.run(debug=True)