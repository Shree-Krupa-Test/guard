import httpx

_http_client: httpx.AsyncClient | None = None


async def init_http_client():
    global _http_client
    _http_client = httpx.AsyncClient(timeout=30.0)
    print("HTTP client started")


async def close_http_client():
    global _http_client
    if _http_client:
        await _http_client.aclose()
        print("HTTP client closed")


def get_http_client() -> httpx.AsyncClient:
    if _http_client is None:
        raise RuntimeError("HTTP client not initialized")
    return _http_client