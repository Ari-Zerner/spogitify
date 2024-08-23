from flask import Flask, redirect, request, session
from spogitify import *
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify
import time
import uuid
import os
import yaml

app = Flask(__name__)
app.secret_key = os.urandom(24)

def sp_oauth():
    return SpotifyOAuth(
        client_id=app.config['SPOTIFY_CLIENT_ID'],
        client_secret=app.config['SPOTIFY_CLIENT_SECRET'],
        redirect_uri=app.config['SPOTIFY_REDIRECT_URI'],
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
        setup_user()
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

def setup_app():
    # Load app config
    app.config.from_file('config.yaml', load=yaml.safe_load)
    
    # Ensure required fields are present
    fields = ['SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET', 'SPOTIFY_REDIRECT_URI', 'USERS_DIR']
    for field in fields:
        if field not in app.config:
            raise ValueError(f"{field} must be set in config.yaml")
    
    if 'users' not in app.config:
        app.config['users'] = {}
        
    os.makedirs(app.config['USERS_DIR'], exist_ok=True)

def setup_user():
    user_id = session.get('user_id')
    if not user_id:
        return
    
    user_dir = os.path.join(app.config['USERS_DIR'], user_id)
    
    os.makedirs(user_dir, exist_ok=True)
    
    # Load user config
    if user_id not in app.config['users']:
        app.config['users'][user_id] = {}
    
    default_config = {
        'PLAYLISTS_DIR': 'playlists',
        'PLAYLIST_METADATA_FILENAME': 'playlists_metadata.csv',
        'REMOTE_URL': None,
        'EXCLUDE_SPOTIFY_PLAYLISTS': True,
        'EXCLUDE_PLAYLISTS': []
    }
    app.config['users'][user_id].update(default_config)
    
    user_config_path = os.path.join(user_dir, 'config.yaml')
    if os.path.exists(user_config_path):
        with open(user_config_path, 'r') as file:
            user_config = yaml.safe_load(file)
            if user_config:
                app.config['users'][user_id].update(user_config)
    
    app.config['users'][user_id]['ARCHIVE_DIR'] = os.path.join(user_dir, 'archive')

if __name__ == '__main__':
    setup_app()
    app.run(debug=True)