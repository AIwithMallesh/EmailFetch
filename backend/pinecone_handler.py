import os
import json
import time
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

class PineconeHandler:
    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME")
        
        if not self.api_key or not self.index_name:
            raise ValueError("Pinecone API Key or Index Name missing in .env")
            
        self.pc = Pinecone(api_key=self.api_key)
        self.index = self.pc.Index(self.index_name)
        
        # Model for inference
        self.model = 'multilingual-e5-large'

    def embed_and_upsert(self, faqs):
        """
        Input: List of FAQ dictionaries.
        Output: Count of upserted items.
        """
        if not faqs:
            return 0
            
        records = []
        
        # Prepare data for embedding
        inputs = []
        # Store metadata map to align with inputs
        meta_map = [] 

        for faq in faqs:
            # Create a rich text representation for embedding
            text = f"Question: {faq['question']}\nAnswer: {faq['answer']}"
            inputs.append(text)
            meta_map.append(faq)
            
        try:
            # 1. Generate Embeddings using Pinecone Inference
            # We treat these as 'passage' type for storage
            embeddings = self.pc.inference.embed(
                model=self.model,
                inputs=inputs,
                parameters={"input_type": "passage", "truncate": "END"}
            )
            
            # 2. Prepare Match Records
            for i, embedding_obj in enumerate(embeddings):
                # The response object structure: 
                # [{'values': [...], 'text': ...}] or similar depending on client version
                # In v6, it returns a list of objects with 'values'
                
                vector = embedding_obj['values']
                faq = meta_map[i]
                
                # Metadata to store
                metadata = {
                    "question": faq['question'],
                    "answer": faq['answer'],
                    "topic": faq.get('topic', 'General'),
                    "source_id": faq.get('source_email_id'),
                    "text": inputs[i] # Store full text for RAG context
                }
                
                records.append({
                    "id": faq.get('source_email_id'),
                    "values": vector,
                    "metadata": metadata
                })
                
            # 3. Upsert to Index
            if records:
                self.index.upsert(vectors=records)
                print(f"✅ Upserted {len(records)} vectors to Pinecone.")
                return len(records)
                
        except Exception as e:
            print(f"❌ Pinecone Error: {e}")
            return 0
        
        return 0

    def search_similar(self, query, top_k=3):
        """
        Searches Pinecone for similar FAQs.
        """
        try:
            # Embed the query
            query_embedding = self.pc.inference.embed(
                model=self.model,
                inputs=[query],
                parameters={"input_type": "query"}
            )
            
            volume = query_embedding[0]['values']
            
            # Query Index
            results = self.index.query(
                vector=volume,
                top_k=top_k,
                include_metadata=True
            )
            
            return results['matches']
            
        except Exception as e:
            print(f"❌ Search Error: {e}")
            return []
