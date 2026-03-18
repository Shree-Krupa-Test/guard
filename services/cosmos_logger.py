# services/cosmos_logger.py

from azure.cosmos import CosmosClient, PartitionKey
import os

# Load Cosmos DB settings from environment variables or define here
COSMOS_ENDPOINT = os.getenv("COSMOS_URI", "https://<your-account>.documents.azure.com:443/")
COSMOS_KEY = os.getenv("COSMOS_KEY", "<your-primary-key>")
DATABASE_NAME = os.getenv("COSMOS_DATABASE", "devguard")
CONTAINER_NAME = os.getenv("COSMOS_CONTAINER", "chat_logs")  # match your container name

# Initialize Cosmos client
client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)

# Get (or create) the database
try:
    database = client.create_database_if_not_exists(id=DATABASE_NAME)
except Exception as e:
    # If already exists, get it
    database = client.get_database_client(DATABASE_NAME)

# Get (or create) the container with proper partition key
try:
    container = database.create_container_if_not_exists(
        id=CONTAINER_NAME,
        partition_key=PartitionKey(path="/project_id"),  # match your Azure portal
        offer_throughput=400  # optional; remove if using autoscale/free tier
    )
except Exception as e:
    # If container already exists, just get it
    container = database.get_container_client(CONTAINER_NAME)


# Function to log a chat message
def log_chat(project_id: str, user_input: str, bot_response: str):
    """
    Logs a chat interaction to Cosmos DB.

    :param project_id: The project identifier (must match partition key)
    :param user_input: The user message
    :param bot_response: The LLM or bot response
    """
    item = {
        "project_id": project_id,  # important: matches partition key
        "user_input": user_input,
        "bot_response": bot_response
    }
    container.create_item(body=item)
    print(f"Logged chat for project {project_id}")