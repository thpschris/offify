"""
Spotify to YouTube Music Playlist Migrator using YTMusic API
"""

import os
import json
import time
import logging
import argparse
from difflib import SequenceMatcher
from typing import Dict, List, Optional
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic, OAuthCredentials

# Configure logging
file_handler = logging.FileHandler('playlist_migration.log', encoding='utf-8')
stream_handler = logging.StreamHandler()

# Set format for both handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Configure root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

load_dotenv()

class PlaylistMigrator:
    def __init__(self):
        self.playlists_store_file = 'playlists_store.json'
        self.playlists_store = self._load_playlists_store()
        # Spotify API setup with OAuth
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
            redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback'),
            scope='playlist-read-private playlist-read-collaborative'
        ))
        
        # YouTube Music API setup
        client_id = os.getenv('YT_CLIENT_ID')
        client_secret = os.getenv('YT_CLIENT_SECRET')
        
        if not all([client_id, client_secret]):
            raise ValueError("YouTube Music client ID and secret are required. Add YT_CLIENT_ID and YT_CLIENT_SECRET to .env")
            
        self.ytmusic = YTMusic('oauth.json', oauth_credentials=OAuthCredentials(
            client_id=client_id,
            client_secret=client_secret
        ))
        
        self.cache = {}
        self.base_delay = 1.0  # Base delay between API calls

    def _similarity_ratio(self, a, b):
        """Fuzzy matching for strings"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def get_spotify_playlist(self, playlist_id):
        """Fetch Spotify playlist metadata"""
        try:
            playlist = self.sp.playlist(playlist_id)
            tracks = []
            results = self.sp.playlist_tracks(playlist_id)
            while results:
                tracks.extend(results['items'])
                results = self.sp.next(results)
            return {
                'name': playlist['name'],
                'tracks': [{
                    'title': item['track']['name'],
                    'artist': item['track']['artists'][0]['name'],
                    'id': item['track']['id'],
                    'duration_ms': item['track']['duration_ms']
                } for item in tracks if item['track']]
            }
        except Exception as e:
            logging.error(f"Spotify API Error: {str(e)}")
            raise

    def search_youtube_music(self, track):
        """Search for a track on YouTube Music"""
        try:
            query = f"{track['artist']} {track['title']}"
            results = self.ytmusic.search(query, filter='songs', limit=5)
            
            if not results:
                logging.warning(f"No results found for {query}")
                return None
                
            best_match = None
            best_score = 0
            track_duration = track['duration_ms']
            duration_tolerance = 0.15  # 15% tolerance
            
            for result in results:
                # Skip results without required fields
                if not all(k in result for k in ['title', 'artists', 'duration_seconds']):
                    continue
                    
                # Convert duration to milliseconds for comparison
                yt_duration = result['duration_seconds'] * 1000
                duration_diff = abs(yt_duration - track_duration) / track_duration
                
                if duration_diff > duration_tolerance:
                    continue
                
                # Calculate similarity scores
                title_score = self._similarity_ratio(track['title'], result['title'])
                artist_score = max(
                    self._similarity_ratio(track['artist'], artist['name'])
                    for artist in result['artists']
                )
                
                # Weight the scores (title and artist equally important)
                combined_score = (title_score * 0.5) + (artist_score * 0.5)
                
                # Check if this is the best match so far
                if combined_score > best_score:
                    best_score = combined_score
                    best_match = result
                    logging.info(f"New best match for '{track['title']}': {result['title']} (score={combined_score:.2f})")
            
            # Return the video ID if we found a good match
            if best_match and best_score > 0.6:  # Minimum threshold for acceptance
                return best_match['videoId']
            else:
                logging.warning(f"No good match found for {track['title']}")
                return None
                
        except Exception as e:
            logging.error(f"YouTube Music search error: {str(e)}")
            return None

    def create_youtube_playlist(self, name):
        """Create YouTube Music playlist"""
        try:
            playlist_id = self.ytmusic.create_playlist(
                title=name,
                description="Migrated from Spotify",
                privacy_status="PRIVATE"
            )
            logging.info(f"Created playlist: {name} ({playlist_id})")
            return playlist_id
        except Exception as e:
            logging.error(f"Failed to create playlist: {str(e)}")
            raise

    def _load_playlists_store(self) -> Dict:
        """Load or create playlists store"""
        if os.path.exists(self.playlists_store_file):
            with open(self.playlists_store_file, 'r') as f:
                return json.load(f)
        return {'playlists': {}}

    def _save_playlists_store(self):
        """Save playlists store"""
        with open(self.playlists_store_file, 'w') as f:
            json.dump(self.playlists_store, f, indent=2)

    def get_all_spotify_playlists(self) -> List[Dict]:
        """Get all user's Spotify playlists"""
        try:
            playlists = []
            results = self.sp.current_user_playlists()
            while results:
                playlists.extend(results['items'])
                results = self.sp.next(results) if results['next'] else None
            return [{
                'id': playlist['id'],
                'name': playlist['name'],
                'tracks_total': playlist['tracks']['total']
            } for playlist in playlists]
        except Exception as e:
            logging.error(f"Failed to get Spotify playlists: {str(e)}")
            return []

    def get_youtube_playlists(self) -> Dict[str, str]:
        """Get all YouTube Music playlists"""
        try:
            playlists = self.ytmusic.get_library_playlists(limit=None)
            return {
                playlist['title']: playlist['playlistId'] 
                for playlist in playlists
            }
        except Exception as e:
            logging.error(f"Failed to get YouTube playlists: {str(e)}")
            return {}

    def update_youtube_playlist(self, playlist_id: str, tracks: List[Dict]) -> None:
        """Update existing YouTube Music playlist"""
        try:
            # Get current tracks in the playlist
            current_tracks = self.ytmusic.get_playlist(playlist_id, limit=None)['tracks']
            current_ids = {track['videoId'] for track in current_tracks}
            
            # Find tracks to add (not in current_ids)
            for track in tracks:
                video_id = self.search_youtube_music(track)
                if video_id and video_id not in current_ids:
                    try:
                        self.ytmusic.add_playlist_items(
                            playlistId=playlist_id,
                            videoIds=[video_id]
                        )
                        logging.info(f"Added to playlist: {track['title']} -> {video_id}")
                        time.sleep(self.base_delay)
                    except Exception as e:
                        logging.error(f"Failed to add video to playlist: {str(e)}")
        except Exception as e:
            logging.error(f"Failed to update playlist: {str(e)}")

    def migrate_playlist(self, spotify_id: str, update_existing: bool = True) -> Optional[str]:
        """Main migration workflow"""
        try:
            # Check if playlist was previously migrated
            if spotify_id in self.playlists_store['playlists']:
                stored_info = self.playlists_store['playlists'][spotify_id]
                if update_existing:
                    logging.info(f"Updating existing playlist: {stored_info['name']}")
                    playlist = self.get_spotify_playlist(spotify_id)
                    self.update_youtube_playlist(stored_info['youtube_id'], playlist['tracks'])
                    return stored_info['youtube_id']
                else:
                    logging.info(f"Playlist already exists: {stored_info['name']}")
                    return stored_info['youtube_id']

            # Get Spotify playlist data
            playlist = self.get_spotify_playlist(spotify_id)
            
            # Create new YouTube Music playlist
            youtube_id = self.create_youtube_playlist(playlist['name'])
            
            # Store mapping
            self.playlists_store['playlists'][spotify_id] = {
                'name': playlist['name'],
                'youtube_id': youtube_id,
                'last_updated': time.time()
            }
            self._save_playlists_store()
            
            # Add tracks
            for track in playlist['tracks']:
                video_id = self.search_youtube_music(track)
                if video_id:
                    try:
                        self.ytmusic.add_playlist_items(
                            playlistId=youtube_id,
                            videoIds=[video_id]
                        )
                        logging.info(f"Added to playlist: {track['title']} -> {video_id}")
                        time.sleep(self.base_delay)
                    except Exception as e:
                        logging.error(f"Failed to add video to playlist: {str(e)}")
                else:
                    logging.warning(f"No match found for {track['title']}")
            
            return youtube_id
            
        except Exception as e:
            logging.error(f"Migration failed: {str(e)}")
            return None

    def migrate_all_playlists(self, update_existing: bool = True) -> None:
        """Migrate all user's Spotify playlists"""
        playlists = self.get_all_spotify_playlists()
        total = len(playlists)
        
        for i, playlist in enumerate(playlists, 1):
            logging.info(f"Processing playlist {i}/{total}: {playlist['name']}")
            self.migrate_playlist(playlist['id'], update_existing)
            time.sleep(self.base_delay)  # Pause between playlists

def main():
    parser = argparse.ArgumentParser(description='Spotify to YouTube Music Playlist Migrator')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--playlist-id', help='Spotify playlist ID to migrate')
    group.add_argument('--all', action='store_true', help='Migrate all playlists')
    parser.add_argument('--no-update', action='store_true', help='Skip updating existing playlists')
    
    args = parser.parse_args()
    
    migrator = PlaylistMigrator()
    if args.all:
        migrator.migrate_all_playlists(update_existing=not args.no_update)
    else:
        migrator.migrate_playlist(args.playlist_id, update_existing=not args.no_update)

if __name__ == "__main__":
    main()
