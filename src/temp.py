# list_models.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()  # reads OPENAI_API_KEY (and OPENAI_ORG if set)

ids = [m.id for m in client.models.list().data]
ids.sort()
print("\n".join(ids))
print("\nHas gpt-4o-mini?", "gpt-4o-mini" in ids)
