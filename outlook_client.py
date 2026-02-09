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

    def save_cache(self):
        """Saves the token cache to a file."""
        if self.cache.has_state_changed:
            with open(self.token_file, 'w') as f:
                f.write(self.cache.serialize())
            print("💾 Token cache saved.")

    def get_token(self, interactive=True):
        # 1. Try to load from local cache (Silent Flow)
        accounts = self.app.get_accounts()
        if accounts:
            print(f"👤 Found account: {accounts[0]['username']}")
            result = self.app.acquire_token_silent(self.scopes, account=accounts[0])
            if result:
                print("✅ Token loaded from cache.")
                self.access_token = result['access_token']
                self.headers = {'Authorization': 'Bearer ' + self.access_token}
                self.save_cache()  # Save in case token was refreshed
                return self.access_token

        # 2. Manual Login (Auth Code Flow)
        print("⚠️  Initiating login...")
        flow = self.app.initiate_auth_code_flow(self.scopes, redirect_uri='http://localhost:8000')
        
        print(f"\n👉  OPEN THIS LINK IN YOUR BROWSER:\n{flow['auth_uri']}\n")
        
        # 3. Listen for the callback automatically
        print("👂 Listening for callback on http://localhost:8000...")
        
        # mutable container to store the result from the request handler
        auth_data = {}

        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                # Parse the URL
                parsed_path = urlparse(self.path)
                query_params = parse_qs(parsed_path.query)
                
                # Store params globally
                if 'code' in query_params:
                    auth_data['query_params'] = query_params
                    
                    # Send 200 OK
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"<h1>Login Successful!</h1><p>You can close this tab and return to the terminal.</p><script>window.close()</script>")
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"<h1>Error: No code found in callback.</h1>")
                
            def log_message(self, format, *args):
                pass # Suppress server logging

        try:
            # Create server
            server = http.server.HTTPServer(('localhost', 8000), CallbackHandler)
            
            # Handle one request then stop
            server.handle_request()
            server.server_close()
            
            if 'query_params' in auth_data:
                print("✅ Captured authentication data automatically.")
                
                # Flatten the query params for MSAL
                query_params = {k: v[0] if isinstance(v, list) else v for k, v in auth_data['query_params'].items()}
                
                result = self.app.acquire_token_by_auth_code_flow(flow, query_params)
                
                if "access_token" in result:
                    self.access_token = result['access_token']
                    self.headers = {'Authorization': 'Bearer ' + self.access_token}
                    self.save_cache()
                    print("✅ Authentication successful! Token saved.")
                    return self.access_token
                else:
                    print(f"❌ Error: {result.get('error_description')}")
                    return None
            else:
                 raise Exception("Server stopped without capturing code.")

        except Exception as e:
            if not interactive:
                 print(f"❌ Automatic capture failed ({e}). Interactive mode disabled.")
                 return None
            
            print(f"❌ Automatic capture failed ({e}). Falling back to manual paste.")
            auth_response = input("Paste the FULL redirect URL (http://localhost:8000/?code=...) here: ").strip()
            if auth_response.startswith("localhost"):
                auth_response = "http://" + auth_response
            
            try:
                parsed_url = urlparse(auth_response)
                query_params = parse_qs(parsed_url.query)
                
                # Flatten params
                query_params = {k: v[0] if isinstance(v, list) else v for k, v in query_params.items()}
                
                result = self.app.acquire_token_by_auth_code_flow(flow, query_params)
                if "access_token" in result:
                    self.access_token = result['access_token']
                    self.headers = {'Authorization': 'Bearer ' + self.access_token}
                    self.save_cache()
                    print("✅ Authentication successful! Token saved.")
                    return self.access_token
            except Exception:
                return None
            return None

    def get_my_profile(self):
        if not self.headers: self.get_token()
        return httpx.get("https://graph.microsoft.com/v1.0/me", headers=self.headers).json()
