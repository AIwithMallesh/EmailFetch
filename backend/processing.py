from bs4 import BeautifulSoup
from datetime import datetime

class ThreadProcessor:
    def __init__(self):
        pass

    def clean_html(self, html_content):
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n").strip()

    def extract_qa_pair(self, thread_emails, my_email_address):
        """
        Input: List of emails in a conversation (from API).
        Output: (question_text, answer_text, answer_message_id) or None
        
        Logic:
        1. Sort emails by date (Newest first).
        2. Find the FIRST email sent by ME (my_email_address). This is the Answer.
        3. Check if the next email (older) is from SOMEONE ELSE. This is the Question.
        4. Validate that this is a direct reply sequence.
        """
        # Sort desc (Newest first)
        sorted_emails = sorted(thread_emails, key=lambda x: x.get('receivedDateTime', ''), reverse=True)
        
        for i in range(len(sorted_emails) - 1):
            latest_email = sorted_emails[i] # Candidate Answer
            previous_email = sorted_emails[i+1] # Candidate Question
            
            sender_address = latest_email.get('sender', {}).get('emailAddress', {}).get('address', '').lower()
            
            # Check if this email is sent by ME (The Support Agent)
            if sender_address == my_email_address.lower():
                
                # Check if previous email is NOT from me (User)
                prev_sender = previous_email.get('sender', {}).get('emailAddress', {}).get('address', '').lower()
                if prev_sender != my_email_address.lower():
                    
                    # We found a potential pair!
                    answer_body = self.clean_html(latest_email.get('body', {}).get('content', ''))
                    question_body = self.clean_html(previous_email.get('body', {}).get('content', ''))
                    
                    # Filter out short/empty messages
                    if len(answer_body) < 10 or len(question_body) < 10:
                        continue
                        
                    return {
                        "question": question_body,
                        "answer": answer_body,
                        "id": latest_email.get('id'), # Use Answer ID as unique key
                        "subject": latest_email.get('subject'),
                        "timestamp": latest_email.get('receivedDateTime')
                    }
        
        return None
