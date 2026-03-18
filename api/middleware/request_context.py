import time
from datetime import datetime
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
 
# simple counter for readable request ids
REQUEST_COUNTER = 0
 
 
def generate_request_id():
 
    global REQUEST_COUNTER
    REQUEST_COUNTER += 1
 
    year = datetime.utcnow().year
 
    return f"DG-{year}-{REQUEST_COUNTER:04d}"
 
 
class RequestContextMiddleware(BaseHTTPMiddleware):
 
    async def dispatch(self, request: Request, call_next):
 
        start_time = time.time()
 
        # generate user friendly request id
        request_id = generate_request_id()
 
        request.state.request_id = request_id
 
        response = await call_next(request)
 
        latency_ms = (time.time() - start_time) * 1000
 
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Latency-MS"] = str(round(latency_ms, 2))
 
        return response