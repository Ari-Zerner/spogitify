import os
import csv
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from git import Repo
import yaml

# Read configuration from YAML file
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# Get configuration values with default fallbacks
archive_dir = os.path.expanduser(config.get('archive_dir', 'spotify-archive'))
playlists_dir = config.get('playlists_dir', 'playlists')
playlist_metadata_filename = config.get('playlist_metadata_filename', 'playlists_metadata.csv')

def get_spotify_client():
    """
    Creates a Spotify client object using environment variables for credentials.
    """
    client_id = os.environ.get('SPOTIFY_CLIENT_ID')
    client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
    redirect_uri = 'http://localhost:8888/callback'

    if not client_id or not client_secret:
        print('Error: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in the environment.')
        exit(1)

    return spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope='user-library-read playlist-read-private'))

def fetch_playlists(sp):
    """
    Fetches all playlists for the authenticated user.
    """
    playlists = []
    results = sp.current_user_playlists()
    while results:
        playlists.extend(results['items'])
        results = sp.next(results)
    playlists = [playlist for playlist in playlists if playlist['owner']['id'] != 'spotify']
    playlists.sort(key=lambda playlist: playlist['id'])
    return playlists

def artists_string(artists):
    """
    Returns a comma-separated string of artist names or 'Unknown Artist' if no artist names are available.
    """
    if artists:
        artist_names = []
        for artist in artists:
            name = artist.get('name')
            if name:
                artist_names.append(name)
        if artist_names:
            return ', '.join(artist_names)
    return 'Unknown Artist'

def export_playlists_metadata(sp, playlists):
    """
    Creates a CSV file with playlist metadata (name, owner, number of songs, and ID).
    """
    with open(f'{archive_dir}/{playlist_metadata_filename}', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['name', 'owner', 'num_songs', 'id'])

        for playlist in playlists:
            name = playlist['name']
            owner = playlist['owner']['display_name']
            length = playlist['tracks']['total']
            id = playlist['id']

            writer.writerow([name, owner, length, id])

def export_playlists(sp, playlists):
    """
    Exports each playlist as a separate CSV file in the playlists folder,
    with fields ['name', 'artist', 'id', 'added_at', 'added_by'].
    """
    for playlist in playlists:
        playlist_name = playlist['name'].replace('/', '_')
        print(f'Exporting playlist: {playlist_name}')
        filename = f'{archive_dir}/{playlists_dir}/{playlist_name}.csv'

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['name', 'artist', 'id', 'added_at', 'added_by'])

            items = []
            results = sp.playlist_tracks(playlist['id'])
            while results:
                items.extend(results['items'])
                results = sp.next(results)

            for item in items:
                track = item['track']
                name = track['name']
                artist = artists_string(track['artists'])
                id = track['id']
                added_at = item.get('added_at', '')
                added_by = item.get('added_by', {}).get('id', '')

                writer.writerow([name, artist, id, added_at, added_by])

def commit_changes():
    """
    Commits any changes in `archive_dir` with the commit message "Update <timestamp>".
    """
    repo = Repo.init(archive_dir)
    repo.index.add([playlists_dir, playlist_metadata_filename])
    if repo.is_dirty(): # Don't commit if there are no changes
        print('Committing changes')
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        has_commits = bool(repo.git.rev_list('--all'))
        if has_commits:
            commit_message = f"Update {timestamp}"
        else:
            commit_message = f"Initial sync {timestamp}"
        repo.index.commit(commit_message)
    else:
        print('No changes to commit')

def main():
    sp = get_spotify_client()
    playlists = fetch_playlists(sp)
    os.makedirs(f'{archive_dir}/{playlists_dir}', exist_ok=True)
    export_playlists_metadata(sp, playlists)
    export_playlists(sp, playlists)
    commit_changes()

if __name__ == '__main__':
    main()