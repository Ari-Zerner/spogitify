import os
import csv
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth

playlist_dir = 'playlists'
playlist_metadata_filename = 'playlists_metadata.csv'

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

def export_playlists(sp, playlists):
    """
    Exports each playlist as a separate CSV file in the 'playlists' folder,
    with fields ['name', 'artist', 'id', 'added_at', 'added_by'].
    """
    os.makedirs('playlists', exist_ok=True)

    for playlist in playlists:
        playlist_name = playlist['name'].replace('/', '_')
        print(f'Exporting playlist: {playlist_name}')
        filename = f"playlists/{playlist_name}.csv"

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

def export_playlists_metadata(sp, playlists):
    """
    Creates a CSV file with playlist metadata (name, owner, number of songs, and ID).
    """
    with open(playlist_metadata_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['name', 'owner', 'num_songs', 'id'])

        for playlist in playlists:
            name = playlist['name']
            owner = playlist['owner']['display_name']
            length = playlist['tracks']['total']
            id = playlist['id']

            writer.writerow([name, owner, length, id])

def main():
    sp = get_spotify_client()
    playlists = fetch_playlists(sp)
    export_playlists_metadata(sp, playlists)
    export_playlists(sp, playlists)

if __name__ == '__main__':
    main()