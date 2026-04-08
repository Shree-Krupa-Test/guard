import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ServiceRequestError
from azure.core.pipeline.transport import RequestsTransport

load_dotenv(override=True)

endpoint = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT", "").strip().rstrip("/")
key = os.getenv("AZURE_CONTENT_SAFETY_KEY")

print("Connecting to Azure Content Safety...")

if not endpoint or not key:
    raise RuntimeError("Azure Content Safety credentials missing in .env")

parsed = urlparse(endpoint)
if parsed.scheme != "https" or not parsed.netloc:
    raise RuntimeError(
        "Invalid AZURE_CONTENT_SAFETY_ENDPOINT. Expected format: "
        "https://<resource>.cognitiveservices.azure.com"
    )

transport = RequestsTransport(use_env_settings=False)
client = ContentSafetyClient(endpoint, AzureKeyCredential(key), transport=transport)

text = "I want to harm someone."
request = AnalyzeTextOptions(text=text)

try:
    response = client.analyze_text(request)
except ServiceRequestError as exc:
    raise RuntimeError(
        f"Could not reach Azure Content Safety at {endpoint}. "
        "Verify that the resource name is correct and that DNS/network access is available."
    ) from exc

print("Connected successfully!\n")
print("Content Safety Analysis:")
for category in response.categories_analysis:
    print(f"{category.category}: severity {category.severity}")
