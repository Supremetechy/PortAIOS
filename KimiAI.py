import requests
import json

url = "https://api.fireworks.ai/inference/v1/completions"
payload = {
  "model": "accounts/fireworks/models/glm-5p2",
  "max_tokens": 131072,
  "top_k": 40,
  "presence_penalty": 0,
  "frequency_penalty": 0,
  "prompt": "Hello, how are you?"
}
headers = {
  "Accept": "application/json",
  "Content-Type": "application/json",
  "Authorization": "Bearer <FIREWORKS_API_KEY>"
}
requests.request("POST", url, headers=headers, data=json.dumps(payload))