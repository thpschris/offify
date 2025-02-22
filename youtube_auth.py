"""YouTube OAuth2 authentication handler"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

class YouTubeAuth:
    """Handles YouTube OAuth2 authentication flow"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.force-ssl',
        'https://www.googleapis.com/auth/youtube'
    ]
    
    def __init__(self, credentials_file='client_secrets.json', token_file='token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        
    def get_credentials(self):
        """Get valid user credentials from storage or initiate OAuth2 flow.
        
        Returns:
            Credentials: The obtained credentials.
        """
        credentials = None
        
        # Load existing token if it exists
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                credentials = pickle.load(token)
        
        # If credentials are invalid or don't exist, refresh or run flow
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                credentials = flow.run_local_server(port=0)
            
            # Save credentials for future use
            with open(self.token_file, 'wb') as token:
                pickle.dump(credentials, token)
        
        return credentials
