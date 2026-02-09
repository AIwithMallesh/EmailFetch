import httpx
from outlook_client import OutlookService

def get_all_emails(outlook, max_count=50):
    """
    Fetches emails from the user's inbox.
    
    Args:
        outlook: The authenticated OutlookService instance.
        max_count: Maximum number of emails to retrieve (use 9999 for 'all')
    """
    print(f"🔄 Connecting to Outlook...")
    
    # 1. Ensure we are logged in
    token = outlook.get_token()
    if not token:
        print("❌ Login failed. Cannot retrieve emails.")
        return []

    # 2. API Setup
    endpoint = "https://graph.microsoft.com/v1.0/me/messages"
    
    # Optimize the request: 
    # - Get 50 at a time ($top)
    # - Sort by newest first ($orderby)
    # - Only get fields we need ($select) to make it faster
    params = {
        "$top": "50",
        "$orderby": "receivedDateTime DESC",
        "$select": "sender,subject,receivedDateTime,bodyPreview"
    }

    all_messages = []
    
    print("📥 Starting download...")

    # 3. Pagination Loop (The "Next Page" Logic)
    while endpoint and len(all_messages) < max_count:
        try:
            # Make the request
            response = httpx.get(endpoint, headers=outlook.headers, params=params)
            response.raise_for_status() # Raise error if 401/403/500
            
            data = response.json()
            messages = data.get('value', [])
            
            # Add this batch to our total list
            all_messages.extend(messages)
            print(f"   ...Fetched {len(messages)} emails (Total: {len(all_messages)})")
            
            # 4. Check for the "Next Page" Link
            # If Microsoft has more emails, they give us a specifically formatted URL
            endpoint = data.get('@odata.nextLink')
            
            # Important: The 'nextLink' already contains the params (top, select, etc.)
            # so we must clear our manual params for the next loop iteration.
            params = None 
            
            if len(all_messages) >= max_count:
                print("🛑 Reached email limit.")
                break
                
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP Error: {e}")
            break
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            break

    return all_messages

# --- Execution ---
if __name__ == "__main__":
    # Initialize your auth class
    my_app = OutlookService()
    
    # Fetch the emails (Change 50 to 1000 if you want more)
    emails = get_all_emails(my_app, max_count=20)
    
    print(f"\n✅ Completed! Found {len(emails)} emails.\n")
    print("-" * 60)
    
    # Print a nice summary
    for i, email in enumerate(emails, 1):
        sender_name = email.get('sender', {}).get('emailAddress', {}).get('name', 'Unknown')
        subject = email.get('subject', '(No Subject)')
        preview = email.get('bodyPreview', '').replace('\n', ' ')[:50] # First 50 chars
        
        print(f"{i}. [{sender_name}] {subject}")
        print(f"   Excerpt: {preview}...\n")
