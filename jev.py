import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.typesafe.ai/v1/systemone"
API_KEY = os.getenv("TYPESAFE_API_KEY")

def call_jev(state: str, questions: dict, model: str = "jev-latest") -> dict:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "state": state,
        "questions": questions,
    }
    response = requests.post(API_URL, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()