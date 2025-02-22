# Offify - Spotify to YouTube Music Playlist Migrator

A Python tool to migrate Spotify playlists to YouTube Music while maintaining track metadata and validating matches. Features intelligent track matching, progress tracking, and batch migration capabilities.

## Features

- 🎵 Migrate single or all Spotify playlists to YouTube Music
- 🔍 Smart track matching with multiple validation checks:
  - Fuzzy matching for artist/title comparison
  - Duration-based validation (15% tolerance)
  - Minimum similarity threshold (0.6)
- 📁 Progress tracking with JSON storage
- 🔄 Update existing playlists
- 📊 Detailed logging system
- ⏱️ Rate limiting protection
- 🎯 Batch migration support

## Prerequisites

- Python 3.9+
- Spotify Developer Account ([create here](https://developer.spotify.com/dashboard))
- YouTube Music OAuth credentials ([Google Cloud Console](https://console.cloud.google.com))

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/offify.git
   cd offify
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials**
   - Copy `.env_example` to `.env`
   - Add your Spotify and YouTube Music credentials:
     ```env
     # Spotify OAuth credentials
     SPOTIFY_CLIENT_ID=your_spotify_client_id
     SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
     SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

     # YouTube Music OAuth credentials
     YT_CLIENT_ID=your_youtube_client_id
     YT_CLIENT_SECRET=your_youtube_client_secret
     ```

## Usage

The tool supports two main modes of operation:

1. **Migrate a single playlist**
   ```bash
   python offify.py --playlist-id SPOTIFY_PLAYLIST_ID
   ```

2. **Migrate all playlists**
   ```bash
   python offify.py --all
   ```

### Additional Options

- `--no-update`: Skip updating existing playlists that were previously migrated
   ```bash
   python offify.py --all --no-update
   ```

## Project Structure

```
.
├── offify.py              # Main application logic
├── youtube_auth.py        # YouTube OAuth handler
├── requirements.txt       # Python dependencies
├── .env                  # Environment configuration
├── .env_example          # Environment template
├── README.md             # Documentation
├── playlists_store.json  # Migration progress tracking
└── playlist_migration.log # Operation logs
```

## How It Works

1. **Authentication**
   - Uses Spotify OAuth for playlist access
   - Uses YouTube Music OAuth for playlist creation/modification

2. **Track Matching**
   - Searches YouTube Music using artist and title
   - Validates matches using fuzzy string matching
   - Confirms duration matches within 15% tolerance
   - Requires minimum 0.6 similarity score

3. **Progress Tracking**
   - Stores migrated playlist information in JSON
   - Enables playlist updating and progress resumption
   - Maintains mapping between Spotify and YouTube Music IDs

4. **Rate Limiting**
   - Implements base delay between API calls
   - Helps prevent API quota exhaustion

## Important Notes

- ⚠️ Never commit your `.env` file
- 📊 Check `playlist_migration.log` for detailed operation logs
- 🔄 Previously migrated playlists can be updated with new tracks
- ⏱️ Migration speed is intentionally throttled to respect API limits
- 🎵 Not all tracks may find matches on YouTube Music

## License

MIT License - See [LICENSE](LICENSE) for details

---

**Note**: This tool is provided as-is. Match accuracy depends on YouTube Music's search results and content availability.
