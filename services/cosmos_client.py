# services/cosmos_client.py

import os
from azure.cosmos.aio import CosmosClient
from dotenv import load_dotenv

load_dotenv()

COSMOS_URI = os.getenv("COSMOS_URI")
COSMOS_KEY = os.getenv("COSMOS_KEY")

if not COSMOS_URI or not COSMOS_KEY:
    raise RuntimeError("Cosmos DB credentials missing")

# ✅ Create ONLY ONCE (singleton)
client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)

database = client.get_database_client("devguard")
container = database.get_container_client("token_usage")