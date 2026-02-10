import os
import google.generativeai as genai
import json
from dotenv import load_dotenv

load_dotenv()

class GeminiValidator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        
        genai.configure(api_key=api_key)
        # Using gemini-1.5-flash as stable default, can switch to 2.0-flash-exp if available
        # The user requested '2.5', we will try to use the latest available.
        self.model = genai.GenerativeModel('gemini-2.5-flash') 

    def validate_and_extract(self, question, answer):
        """
        Uses Gemini to check if this is a valid Q&A pair.
        Returns JSON metadata if valid, else None.
        """
        
        prompt = f"""
        Analyze the following email exchange between a User and a Support Agent.
        
        USER QUESTION:
        {question}
        
        --------------------------------------------------
        
        SUPPORT ANSWER:
        {answer}
        
        --------------------------------------------------
        
        TASK:
        1. Is this a valid, helpful Question & Answer pair suitable for an FAQ? (Ignore generic replies like "Thanks", "Ok", "Will check").
        2. If YES: Return a JSON object with:
           - "valid": true
           - "question": (The exact question text)
           - "answer": (The exact answer text)
           - "topic": (A short 1-2 word category)
           - "keywords": (List of 3-5 keywords)
        3. If NO: Return JSON with "valid": false.

        IMPORTANT:
        - Do NOT rewrite or summarize. Use the original text.
        - Output ONLY raw JSON. No markdown ticks.
        """
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean md ticks if present
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
                
            data = json.loads(text)
            
            if data.get("valid"):
                return data
            return None
            
        except Exception as e:
            print(f"Gemini Error: {e}")
            return None
