# Spogitify

Back up your Spotify playlists to Git with version control. Track how your music tastes evolve over time.

## About

Spogitify is a web service that automatically backs up your Spotify playlists to GitHub. Each backup creates a snapshot of your playlists, allowing you to:

- Track how playlists change over time
- See when songs were added or removed
- Keep a permanent record of your music collection

## Usage

1. Visit [Spogitify](https://spogitify-65ba8394f115.herokuapp.com/) or [run locally](#development).
2. Log in with your Spotify account
   NOTE: Spogitify is currently in beta, and users must be allowlisted. [Contact](https://arizerner.com/contact) me for access.
3. Click "Start Backup" to create your first archive
4. View your playlist history on GitHub

## How It Works

1. Authenticates with Spotify OAuth
2. Fetches all your playlists
3. Exports each playlist to JSON:
   - `playlists_metadata.json`: Overview of all playlists
   - `playlists/*.json`: Individual playlist data
4. Commits changes to a GitHub repository

## Privacy & Security

- All backups are stored in public GitHub repositories
- Only playlist data is stored (no personal Spotify data)
- Spotify login uses official OAuth - we never see your password
- GitHub repositories are created under Spogitify's account

## Development

This is an open source project. To run locally:

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Create a Spotify app:
   1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   2. Click "Create app"
   3. Fill in the app details:
      - App name: Choose any name (e.g. "Spogitify Local")
      - Redirect URI: `http://localhost:5000/authorize`
      - Web API: Selected
   4. Click "Save"
   5. Note your Client ID and Client Secret

3. Create a GitHub token:
   1. Go to [GitHub Settings > Developer Settings > Personal Access Tokens > Tokens (classic)](https://github.com/settings/tokens)
   2. Click "Generate new token (classic)"
   3. Fill in the token details:
      - Note: Choose any name (e.g. "Spogitify Local")
      - Expiration: Choose an appropriate duration
      - Scopes: Select `repo` (Full control of private repositories)
   4. Click "Generate token"
   5. Note your token - you won't be able to see it again

4. Set up environment variables:
```
export SPOTIFY_CLIENT_ID=your_client_id
export SPOTIFY_CLIENT_SECRET=your_client_secret
export SPOTIFY_REDIRECT_URI='http://localhost:5000/authorize'
export GITHUB_TOKEN=your_github_token
```

1. Run the development server:
```
python app.py
```
