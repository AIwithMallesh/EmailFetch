import os
import json
import msal
import httpx
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

    def get_token(self):
        # 1. Try to load from local cache (Silent Flow)
        accounts = self.app.get_accounts()
        if accounts:
            print(f"👤 Found account: {accounts[0]['username']}")
            result = self.app.acquire_token_silent(self.scopes, account=accounts[0])
            if result:
                print("✅ Token loaded significantly from cache.")
                self.access_token = result['access_token']
                self.headers = {'Authorization': 'Bearer ' + self.access_token}
                self.save_cache()  # Save in case token was refreshed
                return self.access_token

        # 2. Manual Login (Auth Code Flow)
        print("⚠️  Initiating login...")
        flow = self.app.initiate_auth_code_flow(self.scopes, redirect_uri='http://localhost:8000')
        
        print(f"\n👉  OPEN THIS LINK IN YOUR BROWSER:\n{flow['auth_uri']}\n")
        
        # 3. Listen for the callback automatically
        import socket
        import re

        print("👂 Listening for callback on http://localhost:8000...")
        
        try:
            # Create a simple socket server to capture the code
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('localhost', 8000))
            server.listen(1)
            
            # Wait for the browser to redirect
            client, addr = server.accept()
            request = client.recv(4096).decode('utf-8')
            
            # Send a nice response to the browser
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<h1>Login Successful!</h1><p>You can close this tab and return to your terminal.</p><script>window.close()</script>"
            client.send(response.encode('utf-8'))
            client.close()
            server.close()
            
            # Extract the code from the request
            match = re.search(r"code=([^& ]+)", request)
            if match:
                auth_code = match.group(1)
                print("✅ Captured authentication code automatically.")
            else:
                raise Exception("Could not find 'code' in the callback request.")

            # Exchange code for token
            result = self.app.acquire_token_by_auth_code_flow(flow, {"code": auth_code})
            
            if "access_token" in result:
                self.access_token = result['access_token']
                self.headers = {'Authorization': 'Bearer ' + self.access_token}
                
                # Save the cache after successful login
                self.save_cache()
                
                print("✅ Authentication successful! Token saved.")
                return self.access_token
            else:
                print(f"❌ Error: {result.get('error_description')}")
                return None
                
        except Exception as e:
            print(f"❌ Automatic capture failed ({e}). Falling back to manual paste.")
            # Fallback to manual paste if port 8000 blocked or other issue
            auth_response = input("Paste the FULL redirect URL (http://localhost:8000/?code=...) here: ").strip()
            if auth_response.startswith("localhost"):
                auth_response = "http://" + auth_response
            
            try:
                parsed_url = urlparse(auth_response)
                query_params = parse_qs(parsed_url.query)
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

if __name__ == "__main__":
    outlook = OutlookService()
    token = outlook.get_token()
    if token:
        profile = outlook.get_my_profile()
        print(f"👋 Success! Logged in as: {profile.get('displayName')}")