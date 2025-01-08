import tempfile
from flask import Flask, request, redirect, session, Response
from helpers.config import *
from helpers import spotify, git, files, database, time

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Helper functions

def login_redirect(redirect_url=None):
    session['previous_page'] = redirect_url or request.url
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
        yield from files.write_playlists_metadata(playlists, config)
        yield from files.write_playlist_tracks(playlists, config)
        yield from git.commit_and_push_changes(repo, config)
    except Exception as e:
        yield f"Error: {str(e)}"
        raise e

# Routes

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "healthy"}, 200

@app.route('/login')
def login():
    return login_redirect('/')

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
    
    # Record backup start time
    database.update_user_last_export(session['user_id'])
        
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

@app.route('/last-backup')
def last_backup():
    if 'user_id' not in session:
        return {"error": "Not logged in"}, 401
    
    last_export = database.get_user_last_export(session['user_id'])
    return {
        "last_backup": time.format_time_since(last_export) if last_export else None
    }
    
@app.route('/config', methods=['GET', 'POST'])
def config():
    if 'user_id' not in session:
        return login_redirect()
    
    if request.method == 'POST':
        new_config = {
            EXCLUDE_SPOTIFY_PLAYLISTS_KEY: request.form.get(EXCLUDE_SPOTIFY_PLAYLISTS_KEY) == 'on',
            EXCLUDE_PLAYLISTS_KEY: [p.strip() for p in request.form.get(EXCLUDE_PLAYLISTS_KEY, '').split('\n') if p.strip()],
        }
        database.update_user_config(session['user_id'], new_config)
        return redirect('/')
    
    current_config = config_for_user(session['user_id'])
    
    html = f"""
    <html>
    <head>
        <title>Spogitify - Configuration</title>
        <style>
            .form-group {{ margin: 20px 0; }}
            label {{ display: block; margin-bottom: 5px; }}
            textarea {{ width: 100%; height: 100px; }}
            .button-group {{ display: flex; gap: 10px; }}
            .button-group button {{ flex: 1; }}
            .secondary {{ background: #6c757d !important; }}
        </style>
        <script>
            let formChanged = false;
            
            function trackChanges() {{
                formChanged = true;
            }}
            
            function confirmDiscard() {{
                if (formChanged) {{
                    return confirm('You have unsaved changes. Are you sure you want to go back?');
                }}
                return true;
            }}
        </script>
    </head>
    <body style="max-width: 800px; margin: 40px auto; padding: 0 20px; font-family: system-ui, sans-serif;">
        <h1>Configuration</h1>
        
        <form method="POST" onchange="trackChanges()">
            <div class="form-group">
                <label>
                    <input type="checkbox" name="{EXCLUDE_SPOTIFY_PLAYLISTS_KEY}" 
                           {'checked' if current_config.get(EXCLUDE_SPOTIFY_PLAYLISTS_KEY) else ''}>
                    Exclude Spotify-generated playlists
                </label>
            </div>
            
            <div class="form-group">
                <label for="{EXCLUDE_PLAYLISTS_KEY}">Exclude these playlists (one per line):</label>
                <textarea name="{EXCLUDE_PLAYLISTS_KEY}" id="{EXCLUDE_PLAYLISTS_KEY}">{chr(10).join(current_config.get(EXCLUDE_PLAYLISTS_KEY, []))}</textarea>
            </div>
            
            <div class="button-group" style="margin-top: 30px;">
                <button type="submit" style="background: #1DB954; color: white; border: none; padding: 10px 20px; border-radius: 20px; cursor: pointer; font-size: 16px;">
                    Save Changes
                </button>
                <a href="/" onclick="return confirmDiscard()">
                    <button type="button" style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 20px; cursor: pointer; font-size: 16px; width: 100%;">
                        Cancel
                    </button>
                </a>
            </div>
        </form>
    </body>
    </html>
    """
    return html

@app.route('/')
def home():
    sp = spotify.spotify_client()
    
    # Common button style
    button_style = 'background: #1DB954; color: white; border: none; padding: 10px 20px; border-radius: 20px; cursor: pointer; font-size: 16px;'
    
    # Common HTML header and description
    html = f"""
    <html>
    <head><title>Spogitify - Spotify Playlist Backup</title></head>
    <body style="max-width: 800px; margin: 40px auto; padding: 0 20px; font-family: system-ui, sans-serif;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h1>Spogitify</h1>
            {f'<div>Logged in with Spotify as {sp.me()["display_name"]}</div>' if sp else ''}
        </div>
        <p>Spogitify backs up your Spotify playlists to a Git repository, allowing you to track how your playlists change over time.</p>
        <p>NOTE: Spogitify is currently in beta, and users must be allowlisted. <a href="https://arizerner.com/contact" target="_blank">Contact</a> Ari Zerner for access.</p>
    """
    
    if not sp:
        # Login button for logged-out users
        html += f"""
            <form action="/login" method="get">
                <button type="submit" style="{button_style}">
                    Login with Spotify
                </button>
            </form>
        </body>
        </html>
        """
        return html
    
    # Additional content for logged-in users
    config = config_for_user(session['user_id'])
    repo_url = git.get_remote_url(config)
    last_export = database.get_user_last_export(session['user_id'])
    last_export_text = time.format_time_since(last_export) if last_export else "Never"
    
    html += f"""
        <div style="background: #fff3cd; padding: 15px; border-radius: 4px; margin: 20px 0;">
            <strong>⚠️ Warning:</strong> Your playlist archive will be stored in a public GitHub repository that anyone can view.
        </div>
        <form action="/export" method="get" target="_blank" onsubmit="setTimeout(updateLastBackupTime, 1000)">
            <button type="submit" style="{button_style}">
                Start Backup
            </button>
        </form>
        <div id="last-backup" style="margin: 10px 0; color: #666;">
            Last backup: <span id="last-backup-time">{last_export_text}</span>
        </div>
        <script>
            function updateLastBackupTime() {{
                fetch('/last-backup')
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('last-backup-time').textContent = data.last_backup || 'Never';
                    }});
            }}
        </script>
        {f'''<form action="{repo_url}" method="get" target="_blank" style="margin-bottom: 10px;">
            <button type="submit" style="{button_style}">
                View on GitHub
            </button>
        </form>''' if repo_url else ''}
        <a href="/config" style="text-decoration: none;">
            <button style="{button_style}">Configure</button>
        </a>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    app.run(debug=True)
