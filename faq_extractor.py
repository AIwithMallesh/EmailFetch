import time
import schedule
import os
from dotenv import load_dotenv
from outlook_client import OutlookService
from read_emails import get_all_emails
from backend.processing import ThreadProcessor
from backend.state import StateManager
from backend.gemini import GeminiValidator

# Load environment logic
load_dotenv()

def run_extraction_job():
    print(f"\n🚀 Starting FAQ Extraction Job at {time.strftime('%H:%M:%S')}...")
    
    # 1. Initialize Services
    try:
        outlook = OutlookService()
        token = outlook.get_token(interactive=False) # Ensure we have a token
        if not token:
            print("❌ Outlook Token missing. Skipping run.")
            return

        gemini = GeminiValidator()
        state_db = StateManager()
        processor = ThreadProcessor()
        
        # Get My Email Address (to identify answers)
        me = outlook.get_my_profile().get('mail') or outlook.get_my_profile().get('userPrincipalName')
        print(f"📧 Identifed Support Agent: {me}")

    except Exception as e:
        print(f"❌ Initialization Error: {e}")
        return

    # 2. Fetch Emails (Last 50)
    print("📥 Fetching recent emails...")
    emails = get_all_emails(outlook, max_count=50)
    
    # Group by Conversation
    threads = {}
    for email in emails:
        cid = email.get('conversationId')
        if cid:
            if cid not in threads: threads[cid] = []
            threads[cid].append(email)
            
    print(f"🧵 Found {len(threads)} active threads.")

    # 3. Process Threads
    new_faqs = 0
    
    for cid, thread_emails in threads.items():
        # Check if already processed (optimization: check latest message ID)
        # But for now, we process potential pairs.
        
        pair = processor.extract_qa_pair(thread_emails, me)
        
        if pair:
            msg_id = pair['id']
            
            # Check if this specific Answer has been processed
            if state_db.is_processed(msg_id):
                print(f"⏭️  Skipping processed thread: {pair['subject'][:30]}...")
                continue
                
            print(f"🔍 Analyzing candidate: {pair['subject']}")
            
            # 4. Validate with Gemini
            metadata = gemini.validate_and_extract(pair['question'], pair['answer'])
            
            if metadata:
                print("✅ Valid FAQ Found! Saving...")
                
                # Add extra metadata
                metadata['source_email_id'] = msg_id
                metadata['conversation_id'] = cid
                metadata['timestamp'] = pair['timestamp']
                
                # 5. Save and Mark State
                state_db.save_faq(metadata)
                state_db.mark_processed(msg_id)
                new_faqs += 1
            else:
                print("⚠️  Gemini rejected (Not a valid FAQ).")
                # Optional: Mark as processed anyway so we don't re-check? 
                # Better to leave it in case logic improves, but to avoid loop cost we can mark it.
                state_db.mark_processed(msg_id) 

    print(f"🎉 Job Complete. Extracted {new_faqs} new FAQs.")

def main():
    print("⏳ FAQ Extractor Service Started (Interval: 10 mins)")
    
    # Run once immediately
    run_extraction_job()
    
    # Schedule
    schedule.every(10).minutes.do(run_extraction_job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
