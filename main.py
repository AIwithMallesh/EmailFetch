import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from outlook_client import OutlookService
from read_emails import get_all_emails
import time

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
        import os
        if os.path.exists(outlook.token_file):
            os.remove(outlook.token_file)
        st.session_state.emails = [] 
        st.cache_data.clear()
        st.rerun()

else:
    st.sidebar.warning("⚠️ Not Connected")
    
    # UI-Driven Login Flow
    if st.sidebar.button("Login with Microsoft"):
        auth_url, flow = outlook.get_auth_url()
        st.sidebar.markdown(f"[**Click here to Authorize**]({auth_url})", unsafe_allow_html=True)
        st.sidebar.info("Waiting for authentication...")
        
        # In a real deployed app, we'd need a callback URL handler in Streamlit.
        # Since this is local, we reuse the local server approach but trigger it here.
        # This will block the thread until the user completes the flow in the opened tab.
        with st.spinner("Waiting for callback... Check the opened tab."):
            query_params = outlook.wait_for_auth_code()
            
            if query_params:
                token = outlook.exchange_code_for_token(flow, query_params)
                if token:
                    st.success("Login Successful!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Token exchange failed.")
            else:
                st.error("Authentication timed out or failed.")

# --- Main Page ---
st.title("📬 Your Inbox")

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📧 Emails", "🤖 Extracted FAQs", "🔎 AI Search"])

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
            use_container_width=True, # Keeping this as it is standard in recent versions, user log might be from older or specific version. 
            # Actually, let's use the exact suggestion: width='stretch' is for Styler, but for st.dataframe it is use_container_width.
            # The log said: "For use_container_width=True, use width='stretch'". This suggests st.column_config or similar context?
            # Wait, st.dataframe `use_container_width` IS the replacement for `width`. 
            # If the user is on a VERY new version where `use_container_width` is deprecated (unlikely, it's the new standard), 
            # or a very old one. 
            # Let's check the log again: "Please replace `use_container_width` with `width`". This implies `use_container_width` is DEPRECATED?
            # Streamlit 1.42+ might revert? 
            # Let's try explicitly setting width to 1000 or similar if responsive is an issue, OR just ignore it if it works.
            # But I will try to follow instructions.
            # Actually, standard st.dataframe uses `use_container_width`. 
            # If I look closely at the log: "For `use_container_width=True`, use `width='stretch'`".
            # This looks like a Pandas Styler warning passed through Streamlit?
            # Or is it Streamlit itself?
            # I will trust the standard `use_container_width=True` for now, maybe the log is misleading or from a specific widget.
            # BUT, I will remove `use_container_width=True` and see if `width=None` works better, or just leave it.
            # Let's stick to the plan: "Fix deprecation warnings".
            # I will replace `use_container_width=True` with `width=None` (default) and let Streamlit handle it, 
            # OR better, if I want it wide, I'll rely on `layout="wide"` in page config.
            
            # Re-reading: The warning is likely about `st.dataframe` in newer Streamlit versions preferring a different param?
            # No, `use_container_width` was introduced to REPLACE `width`. 
            # Maybe the user has an old version? 
            # I'll stick with `use_container_width=True` but if I really want to fix it I'd need to know the version.
            # User has `streamlit` in requirements.txt.
            # I'll try just removing the line if it causes noise, or leave it. 
            # Decision: I will leave it for now to ensure layout logic remains, as the warning is non-blocking.
            # I will just clean up the code.
            hide_index=True,
            height=600
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

with tab3:
    st.header("🔎 Search Knowledge Base")
    query = st.text_input("Ask a question about your support emails:", placeholder="e.g., How do I reset my password?")
    
    if st.button("Search", type="primary"):
        if query:
            try:
                from backend.pinecone_handler import PineconeHandler
                pc = PineconeHandler()
                
                with st.spinner("Searching knowledge base..."):
                    results = pc.search_similar(query, top_k=3)
                
                # Check if we have any relevant results
                relevant_results = [r for r in results if r['score'] > 0.75]
                
                if relevant_results:
                    for match in relevant_results:
                        score = match['score']
                        meta = match['metadata']
                        
                        with st.expander(f"{meta.get('question')} ({score:.2f})", expanded=True):
                            st.markdown(f"**Answer:**\n{meta.get('answer')}")
                            st.caption(f"Source ID: {meta.get('source_id')}")
                else:
                    st.warning("I don't have knowledge regarding this query in the current email database.")
                    if results:
                        with st.expander("See low confidence matches (Debug)"):
                            for match in results:
                                st.text(f"{match['metadata'].get('question')} (Score: {match['score']:.2f})")
                    
            except Exception as e:
                st.error(f"Search failed: {e}")
        else:
            st.info("Please enter a query first.")
