import tempfile
from flask import Flask, request, redirect, session, Response
from spogitify import *
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Helper functions

def spotify_oauth():
    config = get_config()
    return SpotifyOAuth(
        client_id=config[SPOTIFY_CLIENT_ID_KEY],
        client_secret=config[SPOTIFY_CLIENT_SECRET_KEY],
        redirect_uri=config[SPOTIFY_REDIRECT_URI_KEY],
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
    config = get_config(archive_dir=archive_dir, user_id=session['user_id'])
    
    # Return initial response with progress indicator
    def generate():
        yield from map(lambda msg: msg + '\n', run_export(sp, config))
        yield "Export complete! Close this tab and view your archive on GitHub."
        
    return Response(generate(), mimetype='text/plain')

@app.route('/')
def home():
    sp = spotify()
    if not sp:
        return login_redirect()
    
    user = sp.me()
    config = get_config(user_id=session['user_id'])
    repo_url = get_remote_url(config)
        
    html = f"""
    <html>
    <head><title>Spogitify - Spotify Playlist Backup</title></head>
    <body style="max-width: 800px; margin: 40px auto; padding: 0 20px; font-family: system-ui, sans-serif;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h1>Spogitify</h1>
            <div>
                Logged in with Spotify as {user['display_name']}
            </div>
        </div>
        <p>Spogitify backs up your Spotify playlists to a Git repository, allowing you to track how your playlists change over time.</p>
        <div style="background: #fff3cd; padding: 15px; border-radius: 4px; margin: 20px 0;">
            <strong>⚠️ Warning:</strong> Your playlist archive will be stored in a public GitHub repository that anyone can view.
        </div>
        <form action="/export" method="get" target="_blank">
            <button type="submit" style="background: #1DB954; color: white; border: none; padding: 10px 20px; border-radius: 20px; cursor: pointer; font-size: 16px;">
                Start Backup
            </button>
        </form>
        {f'''<form action="{repo_url}" method="get" target="_blank">
            <button type="submit" style="background: #1DB954; color: white; border: none; padding: 10px 20px; border-radius: 20px; cursor: pointer; font-size: 16px;">
                View on GitHub
            </button>
        </form>''' if repo_url else ''}
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    app.run(debug=True)
