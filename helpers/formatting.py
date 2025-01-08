from helpers import files, git
from datetime import datetime

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

def track_string(track):
    """
    Returns a string representation of a track. Accepts a track object with 'name' and 'artist' keys or a tuple of (name, artist).
    """
    if isinstance(track, dict):
        return f"{track['name']} by {track['artist']}"
    elif isinstance(track, tuple):
        return f"{track[0]} by {track[1]}"
    else:
        raise ValueError(f"Invalid track object: {track}")

def describe_changes(changes):
    """
    Returns a human-readable description of a changes object as generated by helpers.changes.playlist_changes.
    """
    change_description = "Summary of Changes:\n"
    
    if changes['added_playlists']:
        change_description += "  Added playlists:\n"
        for playlist in changes['added_playlists']:
            change_description += f"  + {playlist['name']}\n"
            
    if changes['removed_playlists']:
        change_description += "\n  Removed playlists:\n"
        for playlist in changes['removed_playlists']:
            change_description += f"  - {playlist['name']}\n"
            
    if changes['changed_playlists']:
        change_description += "\n  Changed playlists:\n"
        for playlist in changes['changed_playlists']:
            if playlist['name'] != playlist['old_name']:
                change_description += f"  ~ {playlist['old_name']} → {playlist['name']}\n"
            else:
                change_description += f"  ~ {playlist['name']}\n"
                
    # Then show track changes for modified playlists
    if changes['changed_playlists']:
        change_description += "\n  Track changes in modified playlists:\n"
        for playlist in changes['changed_playlists']:
            change_description += f"    {playlist['name']}:\n"
            
            if playlist['added_tracks']:
                change_description += "      Added tracks:\n"
                for track in playlist['added_tracks']:
                    change_description += f"      + {track_string(track)}\n"
            if playlist['removed_tracks']:
                change_description += "      Removed tracks:\n"
                for track in playlist['removed_tracks']:
                    change_description += f"      - {track_string(track)}\n"
    
    return change_description

def commit_message(changes):
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    changelog = describe_changes(changes)
    return f"Archive {timestamp}\n\n{changelog}"
