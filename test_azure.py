from dotenv import load_dotenv
import os
from openai import AzureOpenAI

# Force load .env from current directory
load_dotenv(dotenv_path=".env")

print("Loaded KEY:", os.getenv("AZURE_OPENAI_KEY"))

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
key = os.getenv("AZURE_OPENAI_KEY")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

print("Endpoint:", endpoint)
print("Deployment:", deployment)
print("API Version:", api_version)
print("Key starts with:", key[:5] if key else "None")

client = AzureOpenAI(
    api_key=key,
    api_version=api_version,
    azure_endpoint=endpoint
)

response = client.chat.completions.create(
    model=deployment,
    messages=[{"role": "user", "content": "Say hello"}],
)

print("SUCCESS:", response.choices[0].message.content)