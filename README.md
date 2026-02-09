# EmailFetch - Outlook Email Automation

A robust Python tool to authenticate with Microsoft Outlook (Graph API) and retrieve emails in batches. 

## Features
- **Persistent Authentication**: Logs in once and saves the session (`token_cache.json`). No need to sign in every time!
- **Automatic Login Capture**: Handles the OAuth2 callback automatically using a local server. No copy-pasting required.
- **Batch Retrieval**: Fetches thousands of emails efficiently using pagination.
- **Secure**: Uses `python-dotenv` to manage credentials securely.

## Prerequisites
1.  **Python 3.8+**
2.  **Azure App Registration**:
    -   Register an app in [Azure Portal](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade).
    -   **Redirect URI**: Set to `Web` -> `http://localhost:8000`.
    -   **Permissions**: `User.Read`, `Mail.Read`, `Mail.Send`, `Mail.ReadWrite`.
    -   Generate a **Client Secret**.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/AIwithMallesh/EmailFetch.git
    cd EmailFetch
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Create a `.env` file in the root directory:

```env
AZURE_CLIENT_ID=your_client_id_here
AZURE_CLIENT_SECRET=your_client_secret_here
AZURE_TENANT_ID=common
```
*(Use `common` for personal Outlook/Hotmail accounts. script automatically handles multi-tenant auth).*

## Usage

### Read Emails
Run the email reader script:

```bash
python read_emails.py
```

-   **First Run**: It will open your browser for login. Once authorized, close the tab and check the terminal.
-   **Subsequent Runs**: It will use the saved token and fetch emails immediately.

## Project Structure
-   `outlook_client.py`: Handles OAuth2 authentication, token caching, and automatic callback listening.
-   `read_emails.py`: Main script to fetch and display emails.
-   `token_cache.json`: Stores your session (auto-generated, do not commit).
