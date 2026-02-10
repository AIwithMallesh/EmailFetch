import json
import os
from backend.pinecone_handler import PineconeHandler
from backend.state import StateManager

FAQ_FILE = "data/faq_metadata.json"
STATE_FILE = "data/processed_state.json"

def run_vectorization():
    print("🚀 Starting Pinecone Vectorization...")
    
    # 1. Load Data
    if not os.path.exists(FAQ_FILE):
        print("⚠️ No FAQ metadata found.")
        return

    with open(FAQ_FILE, 'r') as f:
        try:
            all_faqs = json.load(f)
        except:
            print("❌ Error reading FAQ file.")
            return

    # 2. Load State (to check what's already vectorized)
    # We can add a "vectorized_ids" field to our state or just query Pinecone.
    # For simplicity, let's track "vectorized_ids" in a new file or key.
    
    vectorized_file = "data/vectorized_state.json"
    vectorized_ids = set()
    if os.path.exists(vectorized_file):
        with open(vectorized_file, 'r') as f:
             vectorized_ids = set(json.load(f))
             
    # 3. Filter New FAQs
    new_faqs = []
    for faq in all_faqs:
        mid = faq.get('source_email_id')
        if mid and mid not in vectorized_ids:
            new_faqs.append(faq)
            
    print(f"📊 Found {len(all_faqs)} total FAQs. {len(new_faqs)} new to vectorize.")
    
    if not new_faqs:
        print("✅ All caught up.")
        return

    # 4. Upload to Pinecone
    try:
        pc = PineconeHandler()
        count = pc.embed_and_upsert(new_faqs)
        
        # 5. Update State
        if count > 0:
            for faq in new_faqs:
                vectorized_ids.add(faq['source_email_id'])
                
            with open(vectorized_file, 'w') as f:
                json.dump(list(vectorized_ids), f)
            print("💾 State updated.")
            
    except Exception as e:
        print(f"❌ Vectorization failed: {e}")

if __name__ == "__main__":
    run_vectorization()
