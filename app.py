import requests
import json

from dotenv import load_dotenv
import os

load_dotenv()

# First API call with reasoning
headers = {
  "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
  "Content-Type": "application/json",
}

response = requests.post(
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

# Extract the assistant message with reasoning_details
response = response.json()
response = response['choices'][0]['message']

# Preserve the assistant message with reasoning_details
messages = [
  {"role": "user", "content": "How many r's are in the word 'strawberry'?"},
  {
    "role": "assistant",
    "content": response.get('content'),
    "reasoning_details": response.get('reasoning_details')  # Pass back unmodified
  },
  {"role": "user", "content": "Are you sure? Think carefully."}
]

# Second API call - model continues reasoning from where it left off
response2 = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers=headers,
  json={
    "model": "arcee-ai/trinity-large-preview:free",
    "messages": messages,  # Includes preserved reasoning_details
    "reasoning": {"enabled": True}
  }
)

# print(response2.json())
print(response2.json()['choices'][0]['message']['content'])
