import os
import webbrowser
import json
import msal
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()




# --- ADD THIS DEBUG BLOCK ---
print("DEBUG CHECK:")
print(f"Client ID found: {os.getenv('AZURE_CLIENT_ID')}")
print(f"Client Secret found: {os.getenv('AZURE_CLIENT_SECRET')}")
# ----------------------------



class OutlookService:
    def __init__(self):
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        # Use 'common' for personal accounts (Outlook.com, Hotmail)
        # Use your Tenant ID if this is a corporate Azure AD account
        self.tenant_id = os.getenv('AZURE_TENANT_ID', 'common') 
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        
        self.scopes = [
            "User.Read",
            "Mail.Read",
            "Mail.Send",
            "Mail.ReadWrite"
        ]
        
        self.token_file = 'token_cache.json'
        
        # Initialize the MSAL App
        self.app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret,
        )
        
        self.access_token = None
        self.headers = None

    def get_token(self):
        """Handles the entire OAuth flow: checks cache first, then asks for login."""
        
        # 1. Try to load from local file
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
                # Check if token is still valid or refreshable
                accounts = self.app.get_accounts()
                if accounts:
                    result = self.app.acquire_token_silent(self.scopes, account=accounts[0])
                    if result:
                        print("✅ Token loaded from cache.")
                        self.access_token = result['access_token']
                        self.headers = {'Authorization': 'Bearer ' + self.access_token}
                        return self.access_token

        # 2. If no valid token, start manual login flow
        print("⚠️ No valid token found. Initiating manual login...")
        flow = self.app.initiate_auth_code_flow(self.scopes, redirect_uri='http://localhost:8000')
        
        print(f"\n👉 Please open this URL in your browser:\n{flow['auth_uri']}\n")
        # webbrowser.open(flow['auth_uri']) # sending via print instead
        
        # 3. Get the code from the user
        auth_response = input("Paste the full redirect URL (http://localhost:8000/?code=...) here: ")
        
        # Parse the code from the URL
        try:
            # We assume the user pastes the full URL
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(auth_response)
            query_params = parse_qs(parsed_url.query)
            
            # Use a dummy dict because acquire_token_by_auth_code_flow expects the structure
            result = self.app.acquire_token_by_auth_code_flow(flow, query_params)
            
            if "access_token" in result:
                self.access_token = result['access_token']
                self.headers = {'Authorization': 'Bearer ' + self.access_token}
                
                # Save token cache for next time
                # Note: This simple save isn't fully secure for production but fine for testing
                with open(self.token_file, 'w') as f:
                    json.dump(result, f)
                
                print("✅ Authentication successful! Token saved.")
                return self.access_token
            else:
                print(f"❌ Error acquiring token: {result.get('error')}")
                print(result.get('error_description'))
                return None
                
        except Exception as e:
            print(f"❌ Error processing URL: {e}")
            return None

    def get_my_profile(self):
        """Test function to get user profile."""
        if not self.headers:
            self.get_token()
            
        endpoint = "https://graph.microsoft.com/v1.0/me"
        response = httpx.get(endpoint, headers=self.headers)
        return response.json()

    def send_email(self, subject, body, to_email):
        """Sends a simple email."""
        if not self.headers:
            self.get_token()
            
        endpoint = "https://graph.microsoft.com/v1.0/me/sendMail"
        
        email_msg = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ]
            }
        }
        
        response = httpx.post(endpoint, headers=self.headers, json=email_msg)
        if response.status_code == 202:
            print(f"✅ Email sent to {to_email}")
        else:
            print(f"❌ Failed to send email: {response.text}")

# --- execution block ---
if __name__ == "__main__":
    outlook = OutlookService()
    
    # 1. Authenticate
    token = outlook.get_token()
    
    if token:
        # 2. Get Profile Info
        profile = outlook.get_my_profile()
        print(f"👋 Hello, {profile.get('displayName')} ({profile.get('mail') or profile.get('userPrincipalName')})")
        
        # 3. OPTIONAL: Send a test email (Uncomment to test)
        # outlook.send_email("Hello from Python", "This is a test email from my script!", "recipient@example.com")
