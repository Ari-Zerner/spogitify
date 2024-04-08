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

3. Set the following environment variables with your Spotify app credentials:
   - `SPOTIFY_CLIENT_ID`: Your Spotify app's Client ID
   - `SPOTIFY_CLIENT_SECRET`: Your Spotify app's Client Secret

   You can set the environment variables using the following commands:

   - For Linux/macOS:
     ```
     export SPOTIFY_CLIENT_ID=your_client_id
     export SPOTIFY_CLIENT_SECRET=your_client_secret
     ```

   - For Windows:
     ```
     set SPOTIFY_CLIENT_ID=your_client_id
     set SPOTIFY_CLIENT_SECRET=your_client_secret
     ```

## Usage

1. Open a terminal or command prompt and navigate to the directory where the Spogitify script is located.

2. Run the script using the following command:
   ```
   python3 spogitify.py
   ```

3. The script will start running and perform the following steps:
   - Authenticate with the Spotify API using your app credentials.
   - Fetch all your playlists (excluding those owned by Spotify).
   - Export each playlist as a separate CSV file in the `archive_dir/playlists_dir` directory.
   - Create a metadata file named `playlist_metadata_filename` in the `archive_dir` directory, containing information about each playlist.
   - Commit the changes to a Git repository in the `archive_dir` directory.

4. Once the script finishes running, you will have a local Git repository in the `archive_dir` directory with your playlist backups and metadata.

## Configuration

Spogitify uses a YAML configuration file named `config.yaml` to store the following settings:

- `archive_dir`: The directory where the playlist backups and metadata will be stored (default: `spotify-archive`).
- `playlists_dir`: The subdirectory within `archive_dir` where the individual playlist CSV files will be stored (default: `playlists`).
- `playlist_metadata_filename`: The name of the CSV file that will contain the playlist metadata (default: `playlists_metadata.csv`).

You can modify these values in the `config.yaml` file to customize the script's behavior. If a value is not provided in the configuration file, the default value will be used.

## Note

- Running the script will create a new commit in the Git repository each time, allowing you to track the history of your playlist backups.

- Make sure to keep your Spotify app credentials secure and do not share them with others.

- The script requires an active internet connection to communicate with the Spotify API.
