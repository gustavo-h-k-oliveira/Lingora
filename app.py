import requests
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
import os

from storage.conversations import save_conversation_as_array

load_dotenv()

# First API call with reasoning
headers = {
  "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
  "Content-Type": "application/json",
}

resp1 = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers=headers,
  data=json.dumps({
    "model": "arcee-ai/trinity-large-preview:free",
    "messages": [
        {
          "role": "user",
          "content": "How many r's are in the word 'strawberry'?"
        }
      ],
    "reasoning": {"enabled": True}
  })
)

# Extract the assistant message with reasoning_details and save raw JSON
resp1_json = resp1.json()
assistant_msg = resp1_json['choices'][0]['message']

# Preserve the assistant message with reasoning_details
messages = [
  {"role": "user", "content": "How many r's are in the word 'strawberry'?"},
  {
    "role": "assistant",
    "content": assistant_msg.get('content'),
    "reasoning_details": assistant_msg.get('reasoning_details')  # Pass back unmodified
  },
  {"role": "user", "content": "Are you sure? Think carefully."}
]

# Second API call - model continues reasoning from where it left off
resp2 = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers=headers,
  json={
    "model": "arcee-ai/trinity-large-preview:free",
    "messages": messages,  # Includes preserved reasoning_details
    "reasoning": {"enabled": True}
  }
)

resp2_json = resp2.json()
print(resp2_json['choices'][0]['message']['content'])

# Save conversation (uses storage module)
conversation = {
  "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
  "model": "arcee-ai/trinity-large-preview:free",
  "messages": messages,
  "raw_response1": resp1_json,
  "raw_response2": resp2_json
}

try:
    save_conversation_as_array("data/conversations.json", conversation)
    print("✅ Conversation saved to data/conversations.json")
except Exception as e:
    print(f"⚠️ Failed to save conversation: {e}")
