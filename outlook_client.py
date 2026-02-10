import os
import json
import msal
import httpx
import http.server
import socketserver
import threading
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs

# Load environment variables
load_dotenv()

class OutlookService:
    def __init__(self):
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        self.tenant_id = os.getenv('AZURE_TENANT_ID', 'common') 
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        
        self.scopes = ["User.Read", "Mail.Read", "Mail.Send", "Mail.ReadWrite"]
        self.token_file = 'token_cache.json'
        
        # Initialize Token Cache
        self.cache = msal.SerializableTokenCache()
        if os.path.exists(self.token_file):
            print(f"📂 Loading token cache from {self.token_file}...")
            with open(self.token_file, 'r') as f:
                self.cache.deserialize(f.read())
        
        self.app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret,
            token_cache=self.cache  # Pass the cache to the app
        )
        self.access_token = None
        self.headers = None

    def get_auth_url(self):
        """Generates the login URL for the user to click."""
        flow = self.app.initiate_auth_code_flow(self.scopes, redirect_uri='http://localhost:8000')
        return flow['auth_uri'], flow

    def wait_for_auth_code(self):
        """
        Starts a local server to listen for the auth code. 
        Blocking call, suitable for a background thread.
        Returns the query params or None.
        """
        auth_data = {}
        
        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_path = urlparse(self.path)
                auth_data['query_params'] = parse_qs(parsed_path.query)
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"<h1>Authentication Complete!</h1><p>You can close this tab and return to the app.</p><script>window.close()</script>")
            
            def log_message(self, format, *args):
                return # Silence logs

        try:
            server = http.server.HTTPServer(('localhost', 8000), CallbackHandler)
            # print("👂 Listening for callback on http://localhost:8000...")
            server.handle_request()
            server.server_close()
            
            if 'query_params' in auth_data:
                # Flatten the query params for MSAL
                return {k: v[0] if isinstance(v, list) else v for k, v in auth_data['query_params'].items()}
        except Exception as e:
            print(f"❌ Server Error: {e}")
            return None
        return None

    def exchange_code_for_token(self, flow, query_params):
        """Exchanges the auth parameters for a token."""
        try:
            result = self.app.acquire_token_by_auth_code_flow(flow, query_params)
            if "access_token" in result:
                self.access_token = result['access_token']
                self.headers = {'Authorization': 'Bearer ' + self.access_token}
                self.save_cache()
                return self.access_token
        except Exception as e:
            print(f"❌ Token Exchange Error: {e}")
        return None

    def save_cache(self):
        """Saves the token cache to a file."""
        if self.cache.has_state_changed:
            with open(self.token_file, 'w') as f:
                f.write(self.cache.serialize())
            print("💾 Token cache saved.")

    def get_token(self, interactive=True):
        # 1. Try Cache
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(self.scopes, account=accounts[0])
            if result:
                self.access_token = result['access_token']
                self.headers = {'Authorization': 'Bearer ' + self.access_token}
                # print("✅ Token loaded from cache.")
                return self.access_token

        if not interactive:
            return None

        # 2. Interactive Login (Terminal only fallback)
        print("⚠️  Initiating login...")
        auth_url, flow = self.get_auth_url()
        print(f"\n👉  OPEN THIS LINK IN YOUR BROWSER:\n{auth_url}\n")
        print("👂 Listening for callback on http://localhost:8000...")
        
        query_params = self.wait_for_auth_code()
        
        if query_params:
            print("✅ Captured authentication data automatically.")
            if self.exchange_code_for_token(flow, query_params):
                print("✅ Authentication successful! Token saved.")
                return self.access_token
        else:
             print("❌ Automatic capture failed.")
             
        return None

    def get_my_profile(self):
        if not self.headers: self.get_token()
        return httpx.get("https://graph.microsoft.com/v1.0/me", headers=self.headers).json()
