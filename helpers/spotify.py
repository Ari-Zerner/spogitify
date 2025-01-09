import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import session
import uuid
from helpers.config import *
from helpers import files, formatting

SPOTIFY_CLIENT_ID = env_var(SPOTIFY_CLIENT_ID_KEY)
SPOTIFY_CLIENT_SECRET = env_var(SPOTIFY_CLIENT_SECRET_KEY)
SPOTIFY_REDIRECT_URI = env_var(SPOTIFY_REDIRECT_URI_KEY)

def spotify_oauth():
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope='user-library-read playlist-read-private',
        cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session),
        state=str(uuid.uuid4())
    )

def spotify_client(sp_oauth=None):
    if not sp_oauth:
        sp_oauth = spotify_oauth()
    if not sp_oauth.validate_token(sp_oauth.get_cached_token()):
        return None
    auth_token = sp_oauth.get_cached_token()['access_token']
    return spotipy.Spotify(auth=auth_token)

def include_playlist(playlist, config):
    """
    Returns True if the playlist should be included in the export.
    """
    if playlist['name'] in config[EXCLUDE_PLAYLISTS_KEY]:
        return False
    return True

def fetch_playlists(sp, config):
    """
    Fetches all playlists for the authenticated user, including track details.
    """
    yield 'Fetching playlists from Spotify...'
    playlists = []
    seen_playlist_ids = set()
    
    # Load existing playlist metadata
    playlists_metadata = files.read_playlists_metadata(config) or {}
    
    results = sp.current_user_playlists()
    while results:
        for item in results['items']:
            if item and item['id'] not in seen_playlist_ids and include_playlist(item, config):
                if item['id'] in playlists_metadata and playlists_metadata[item['id']]['snapshot_id'] == item['snapshot_id']:
                    # If the playlist hasn't changed, reuse saved information
                    yield f"Unchanged playlist: {item['name']}"
                    playlist = playlists_metadata[item['id']]
                    playlist['tracks'] = files.read_playlist_tracks(playlist, config)
                else:
                    yield f"Fetching playlist: {item['name']}"
                    playlist = {
                        'id': item['id'],
                        'name': item['name'],
                        'owner': item['owner']['display_name'],
                        'snapshot_id': item['snapshot_id']
                    }
                    total_length_ms = 0
                    
                    # Fetch tracks for the playlist
                    tracks = []
                    track_results = sp.playlist_tracks(playlist['id'])
                    while track_results:
                        for track_item in track_results['items']:
                            track = track_item['track']
                            if track:
                                track_info = {
                                    'name': track['name'],
                                    'artist': formatting.artists_string(track['artists']),
                                    'id': track['id'],
                                    'added_at': track_item.get('added_at', ''),
                                    'added_by': track_item.get('added_by', {}).get('id', ''),
                                    'length_seconds': track['duration_ms'] // 1000
                                }
                                tracks.append(track_info)
                                total_length_ms += track['duration_ms']
                        track_results = sp.next(track_results)
                    
                    playlist['tracks'] = tracks
                    playlist['num_songs'] = len(tracks)
                    playlist['total_length_seconds'] = total_length_ms // 1000
                    
                playlists.append(playlist)
                seen_playlist_ids.add(item['id'])
                
        results = sp.next(results)
    
    playlists.sort(key=lambda playlist: playlist['id'])
    return playlists