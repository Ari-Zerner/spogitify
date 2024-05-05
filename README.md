# Spogitify

Spogitify is a Python script that allows you to backup your Spotify playlists to a local Git repository. It fetches all your playlists (excluding those owned by Spotify), exports each playlist as a separate CSV file, and creates a metadata file with information about each playlist. The script then commits the changes to a Git repository, allowing you to track the history of your playlist backups.

## Prerequisites

Before running Spogitify, make sure you have the following:

- Python 3.x installed on your system
- A Spotify Developer account and app credentials (Client ID and Client Secret)
- The following Python libraries installed:
  - `spotipy`
  - `gitpython`
  - `pyyaml`

You can install the required libraries using pip:

```
pip install spotipy gitpython pyyaml
```

## Setup

1. Clone the Spogitify repository.

2. Set up your Spotify app credentials:
   - Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and create a new app.
   - Note down the Client ID and Client Secret for your app.
   - Set the Redirect URI to `http://localhost:8888/callback` in your app settings.

3. Copy `example-config.yaml` to `config.yaml` and modify `config.yaml` with your Spotify credentials, as well as any other desired configuration (see [Configuration](#configuration)).

## Usage

### Run Once
1. Open a terminal or command prompt and navigate to the directory where the Spogitify script is located.

2. Run the script using the following command:
   ```
   python3 spogitify.py
   ```

3. The script will start running and perform the following steps:
   - Authenticate with the Spotify API using your app credentials.
   - Fetch all your playlists (except for configured exclusions).
   - Export each playlist as a separate CSV file in a folder in the archive directory.
   - Create a metadata file in the archive directory, containing information about each playlist.
   - Commit the changes to a Git repository in the archive directory.

4. Once the script finishes running, you will have a local Git repository in the archive directory with your playlist backups and metadata.

### Run Daily

To automatically run Spogitify daily:

1. In the project directory, make `setup_cron.sh` executable:
```
chmod +x setup_cron.sh
```

2. Run the setup script:
```
./setup_cron.sh
```

This will set up a daily cron job to run spogitify.py at midnight.

To modify the cron schedule, edit the `cron_schedule` variable in `setup_cron.sh` before running the script.

If you encounter issues, check the system or cron logs, or run `crontab -l` to verify the cron job is scheduled correctly.

## Configuration

Spogitify uses a YAML configuration file named `config.yaml` to store the following settings:

- `spotify_client_id`: Your Spotify app's Client ID (required).
- `spotify_client_secret`: Your Spotify app's Client Secret (required).
- `archive_dir`: The directory where the playlist backups and metadata will be stored (default: `spotify-archive`).
- `playlists_dir`: The subdirectory within `archive_dir` where the individual playlist CSV files will be stored (default: `playlists`).
- `playlist_metadata_filename`: The name of the CSV file that will contain the playlist metadata (default: `playlists_metadata.csv`).
- `exclude_spotify_playlists`: Whether to exclude Spotify-generated playlists from the archive (default: `yes`).
- `exclude_playlists`: A list of specific playlists to exclude from the archive (default: `[]`).

## Note

- Running the script will create a new commit in the Git repository each time, allowing you to track the history of your playlist backups.

- Make sure to keep your Spotify app credentials secure and do not share them with others.

- The script requires an active internet connection to communicate with the Spotify API.
