# services/cosmos_token_store.py
#
# Token Store — tracks per-project token usage in Cosmos DB.
#
# BUG FIX 1: Token quota not enforcing — fixed with AVG_TOKENS_PER_REQUEST buffer.
# BUG FIX 2: Unclosed client session warnings — CosmosClient (azure.cosmos.aio)
#            opens an aiohttp session per instantiation. Fixed by calling
#            self.client.close() in a finally block after every operation.

import os
from azure.cosmos.aio import CosmosClient
from dotenv import load_dotenv

load_dotenv()

COSMOS_URI     = os.getenv("COSMOS_URI")
COSMOS_KEY     = os.getenv("COSMOS_KEY")
DATABASE_NAME  = "devguard"
CONTAINER_NAME = "token_usage"

# Project token budget
MAX_TOKENS = 1000000

# Conservative buffer — blocks if remaining < this value
# Prevents LLM from running when quota is nearly exhausted
AVG_TOKENS_PER_REQUEST = 2000


class TokenStore:

    def __init__(self):
        if not COSMOS_URI:
            raise RuntimeError("COSMOS_URI not found in environment variables")
        if not COSMOS_KEY:
            raise RuntimeError("COSMOS_KEY not found in environment variables")

        print("[Cosmos] Connecting to database...")
        self.client    = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
        self.database  = self.client.get_database_client(DATABASE_NAME)
        self.container = self.database.get_container_client(CONTAINER_NAME)
        print("[Cosmos] Connected successfully.")

    async def _close(self):
        """Closes the aiohttp session opened by CosmosClient."""
        try:
            await self.client.close()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────
    # Get or Create Project Record
    # ──────────────────────────────────────────────────────
    async def get_or_create_project(self, project_id: str):
        try:
            item = await self.container.read_item(
                item=project_id,
                partition_key=project_id
            )
            return item
        except Exception:
            print(f"[Cosmos] Creating new project record: {project_id}")
            new_item = {
                "id":          project_id,
                "project_id":  project_id,
                "tokens_used": 0,
                "token_quota": MAX_TOKENS
            }
            await self.container.create_item(body=new_item)
            return new_item

    # ──────────────────────────────────────────────────────
    # Pre-flight Quota Check (BEFORE LLM call)
    # ──────────────────────────────────────────────────────
    async def check_quota(self, project_id: str, estimated_tokens: int = AVG_TOKENS_PER_REQUEST):
        try:
            item        = await self.get_or_create_project(project_id)
            tokens_used = item["tokens_used"]
            quota       = item["token_quota"]
            remaining   = quota - tokens_used

            if remaining <= 0 or remaining < AVG_TOKENS_PER_REQUEST:
                print(f"[Token Store] Quota EXCEEDED — "
                      f"Used: {tokens_used} / {quota} | Remaining: {remaining}")
                return {
                    "allowed":           False,
                    "tokens_used_total": tokens_used,
                    "tokens_remaining":  remaining,
                    "token_quota":       quota
                }

            print(f"[Token Store] Quota OK — "
                  f"Used: {tokens_used} / {quota} | Remaining: {remaining}")
            return {
                "allowed":           True,
                "tokens_used_total": tokens_used,
                "tokens_remaining":  remaining,
                "token_quota":       quota
            }
        finally:
            await self._close()

    # ──────────────────────────────────────────────────────
    # Update Tokens (AFTER LLM call — actual usage)
    # ──────────────────────────────────────────────────────
    async def update_tokens(self, project_id: str, tokens_used_request: int):
        try:
            item      = await self.get_or_create_project(project_id)
            new_total = item["tokens_used"] + tokens_used_request
            quota     = item["token_quota"]

            item["tokens_used"] = new_total
            await self.container.replace_item(item=item, body=item)

            remaining = quota - new_total
            print(f"[Token Store] Updated — "
                  f"Used: {new_total} / {quota} | Remaining: {remaining}")

            return {
                "tokens_used_request": tokens_used_request,
                "tokens_used_total":   new_total,
                "tokens_remaining":    remaining,
                "token_quota":         quota,
            }
        finally:
            await self._close()