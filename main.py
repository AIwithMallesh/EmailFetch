import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from outlook_client import OutlookService
from read_emails import get_all_emails

# ... (rest of imports/config)

# --- Page Config ---
st.set_page_config(
    page_title="Outlook Email Viewer",
    page_icon="📧",
    layout="wide"
)

# Helper function to clean HTML
def clean_html(html_content):
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    # get_text with separator handles <br> and <p> better
    return soup.get_text(separator="\n").strip()

# --- Session State ---
if 'outlook' not in st.session_state:
    st.session_state.outlook = OutlookService()

if 'emails' not in st.session_state:
    st.session_state.emails = []

# --- Sidebar ---
st.sidebar.title("📧 Connections")

# Initialize logic
outlook = st.session_state.outlook
token = outlook.get_token(interactive=False)

if token:
    st.sidebar.success("✅ Connected to Outlook")
    try:
        profile = outlook.get_my_profile()
        st.sidebar.write(f"**User**: {profile.get('displayName')}")
        st.sidebar.write(f"**Email**: {profile.get('mail') or profile.get('userPrincipalName')}")
    except:
        st.sidebar.warning("Could not fetch profile")

    if st.sidebar.button("Logout (Clear Cache)", type="primary"):
        # Clear token cache
        import os
        if os.path.exists(outlook.token_file):
            os.remove(outlook.token_file)
        st.session_state.emails = [] # Clear loaded emails
        st.cache_data.clear()
        st.rerun()

else:
    st.sidebar.warning("⚠️ Not Connected")
    if st.sidebar.button("Connect Account"):
        # Trigger login flow with interactive=False to prevent hang
        # BUT: We need a way to open the URL.
        # Actually, get_token(interactive=False) will print URL and return None if auto-capture fails.
        # For local execution, auto-capture (http.server) is blocking but works.
        # The 'interactive' flag only guards the fallback input().
        
        token = outlook.get_token(interactive=False)
        if token:
             st.rerun()
        else:
             st.error("Login failed or timed out. Check terminal for details.")

# --- Main Page ---
st.title("📬 Your Inbox")

# --- Tabs ---
tab1, tab2 = st.tabs(["📧 Emails", "🤖 Extracted FAQs"])

with tab1:
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 Refresh Emails"):
            with st.spinner("Fetching emails..."):
                st.session_state.emails = get_all_emails(outlook, max_count=50)

    # --- Display Data ---
    emails = st.session_state.emails

    if emails:
        # Convert to DataFrame for easier handling
        data = []
        for email in emails:
            sender = email.get('sender', {}).get('emailAddress', {}).get('name', 'Unknown')
            sender_email = email.get('sender', {}).get('emailAddress', {}).get('address', '')
            subject = email.get('subject', '(No Subject)')
            received = email.get('receivedDateTime', '')
            body_preview = email.get('bodyPreview', '')
            
            # Get and clean body content
            raw_body = email.get('body', {}).get('content', '')
            clean_body = clean_html(raw_body)
            
            conversation_id = email.get('conversationId', '')
            
            data.append({
                "Sender": sender,
                "Subject": subject,
                "Received": received,
                "Preview": body_preview,
                "Body": clean_body,
                "ConversationID": conversation_id,
                "FullData": email
            })

        df = pd.DataFrame(data)
        
        # --- Main Table ---
        st.subheader("📊 Emails")
        
        # Sort for best visibility
        df = df.sort_values(by="Received", ascending=False)

        st.dataframe(
            df[["Sender", "Subject", "Received", "Body", "ConversationID"]],
            use_container_width=True,
            hide_index=True,
            height=600  # Give it some space
        )

    elif token:
        st.info("No emails loaded. Click 'Refresh Emails' to fetch.")
    else:
        st.info("Please connect your account from the sidebar.")

with tab2:
    st.header("🤖 AI Extracted FAQs")
    st.markdown("These are Question & Answer pairs automatically extracted from your email threads.")
    
    faq_file = "data/faq_metadata.json"
    processed_file = "data/processed_state.json"
    
    import json
    import os
    
    if os.path.exists(faq_file):
        with open(faq_file, "r") as f:
            try:
                faqs = json.load(f)
                if faqs:
                    st.success(f"Found {len(faqs)} FAQs")
                    
                    for i, faq in enumerate(faqs):
                        with st.expander(f"Q: {faq.get('question')[:100]}..."):
                            st.markdown(f"**Question:**\n{faq.get('question')}")
                            st.markdown(f"**Answer:**\n{faq.get('answer')}")
                            st.caption(f"Topic: {faq.get('topic')} | Keywords: {', '.join(faq.get('keywords', []))}")
                            # st.json(faq)
                else:
                    st.warning("No FAQs extracted yet.")
            except:
                st.error("Error reading FAQ file.")
    else:
        st.info("No extracted data found. Run `python faq_extractor.py` to start the process.")
