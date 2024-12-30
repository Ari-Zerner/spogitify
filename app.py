import tempfile
from flask import Flask, request, redirect, session, Response
from helpers.config import *
from helpers import spotify, git, files, formatting

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Helper functions

def login_redirect():
    session['previous_page'] = request.url
    auth_url = spotify.spotify_oauth().get_authorize_url()
    return redirect(auth_url)

def run_export(sp, config):
    """
    Executes the main export process for Spotify playlists.

    This function performs the following steps:
    1. Fetches all playlists from the user's Spotify account.
    2. Sets up the archive directory and initializes/updates the Git repository.
    3. Writes metadata for all playlists to a JSON file.
    4. Writes individual JSON files for each playlist's tracks.
    5. Commits all changes to the Git repository.
    6. Pushes changes to the remote repository if configured.

    Args:
        sp (spotipy.Spotify): An authenticated Spotify client object.
        config (dict): A dictionary containing configuration settings.

    Note:
        This function may take a while to complete, especially for users with many playlists.
        
    Returns:
        A generator of status messages.
    """
    try:
        repo = git.setup_archive(config)
        playlists = yield from spotify.fetch_playlists(sp, config)
        yield from files.write_playlists_metadata_json(playlists, config)
        yield from files.write_playlist_tracks_json(playlists, config)
        commit_message = formatting.commit_message(repo, config)
        yield from git.commit_and_push_changes(repo, config, commit_message)
    except Exception as e:
        yield f"Error: {str(e)}"
        raise e

# Routes

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "healthy"}, 200

@app.route('/authorize')
def authorize():
    sp_oauth = spotify.spotify_oauth()
    sp_oauth.get_access_token(request.args['code'])
    sp = spotify.spotify_client(sp_oauth)
    if sp:
        user_info = sp.me()
        session['user_id'] = user_info['id']
        return redirect(session.pop('previous_page', '/'))
    return {"error": "Failed to get access token"}, 400

@app.route('/export', methods=['GET'])
def export():
    sp = spotify.spotify_client()
    if not sp:
        return login_redirect()
        
    # Create temporary directory for this export
    export_dir = tempfile.mkdtemp()
    archive_dir = os.path.join(export_dir, 'spotify-archive')
    config = {
        **config_for_user(session['user_id']),
        ARCHIVE_DIR_KEY: archive_dir
    }
    
    # Return initial response with progress indicator
    def generate():
        yield from map(lambda msg: msg + '\n', run_export(sp, config))
        yield "Export complete! Close this tab and view your archive on GitHub."
        
    return Response(generate(), mimetype='text/plain')

@app.route('/')
def home():
    sp = spotify.spotify_client()
    if not sp:
        return login_redirect()
    
    user = sp.me()
    config = config_for_user(session['user_id'])
    repo_url = git.get_remote_url(config)
        
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
        <p>NOTE: Spogitify is currently in beta, and users must be allowlisted. <a href="https://arizerner.com/contact" target="_blank">Contact</a> Ari Zerner for access.</p>
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
