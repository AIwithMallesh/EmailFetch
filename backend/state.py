import json
import os

STATE_FILE = "data/processed_state.json"
FAQ_FILE = "data/faq_metadata.json"

class StateManager:
    def __init__(self):
        # Ensure data directory exists
        if not os.path.exists("data"):
            os.makedirs("data")

        # Load processed IDs
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    self.processed_ids = set(json.load(f))
            except json.JSONDecodeError:
                self.processed_ids = set()
        else:
            self.processed_ids = set()

    def is_processed(self, message_id):
        return message_id in self.processed_ids

    def mark_processed(self, message_id):
        self.processed_ids.add(message_id)
        self._save_state()

    def _save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump(list(self.processed_ids), f)

    def save_faq(self, faq_data):
        existing_faqs = []
        if os.path.exists(FAQ_FILE):
            try:
                with open(FAQ_FILE, "r") as f:
                    existing_faqs = json.load(f)
            except json.JSONDecodeError:
                pass
        
        existing_faqs.append(faq_data)
        
        with open(FAQ_FILE, "w") as f:
            json.dump(existing_faqs, f, indent=4)
