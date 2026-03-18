import os
from dotenv import load_dotenv
from azure.ai.contentsafety import ContentSafetyClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.contentsafety.models import AnalyzeTextOptions

load_dotenv()

endpoint = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT")
key = os.getenv("AZURE_CONTENT_SAFETY_KEY")

print("🔄 Connecting to Azure Content Safety...")

if not endpoint or not key:
    raise RuntimeError("❌ Azure Content Safety credentials missing in .env")

client = ContentSafetyClient(endpoint, AzureKeyCredential(key))

text = "I want to harm someone."

request = AnalyzeTextOptions(text=text)

response = client.analyze_text(request)

print("✅ Connected successfully!\n")

print("Content Safety Analysis:")
for category in response.categories_analysis:
    print(f"{category.category}: severity {category.severity}")