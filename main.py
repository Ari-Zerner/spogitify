from os import sendfile
import shutil
import tempfile
from flask import Flask, request, redirect, session, Response, send_file, after_this_request
from spogitify import *
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify
import time
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Helper functions

def setup_app():
    app.config.update(get_config())

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

@app.route('/export', methods=['GET'])
def export():
    sp = spotify()
    if not sp:
        return login_redirect()
        
    # Create temporary directory for this export
    export_dir = tempfile.mkdtemp()
    archive_dir = os.path.join(export_dir, 'spotify-archive')
    config = app.config.copy()
    config['archive_dir'] = archive_dir
    host_url = request.host_url
    
    # Return initial response with progress indicator
    def generate():
        yield from map(lambda msg: msg + '\n', run_export(sp, config))
        
        yield "Creating zip file...\n"
        zip_path = os.path.join(export_dir, 'spotify-archive.zip')
        shutil.make_archive(zip_path[:-4], 'zip', archive_dir)
        yield f"Download zip file: {host_url}download?path={zip_path}\n"
        
    return Response(generate(), mimetype='text/plain')

@app.route('/download')
def download():
    zip_path = request.args['path']
    if not zip_path.endswith('spotify-archive.zip'):
        return {"error": "Path must be a Spotify archive"}, 400
    if not os.path.exists(zip_path):
        return {"error": "File not found"}, 404
    return send_file(zip_path, as_attachment=True, download_name='spotify-archive.zip')

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
