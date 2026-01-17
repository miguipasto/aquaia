"""
Middleware de rate limiting para prevenir abuso de la API.
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
from collections import defaultdict
from typing import Dict, Tuple
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware que implementa rate limiting por IP."""
    
    def __init__(self, app):
        super().__init__(app)
        self.requests: Dict[str, list] = defaultdict(list)
        self.enabled = settings.enable_rate_limit
        self.max_requests = settings.rate_limit_requests
        self.window = settings.rate_limit_window
    
    async def dispatch(self, request: Request, call_next):
        """Procesa la petición aplicando rate limiting."""
        if not self.enabled:
            return await call_next(request)
        
        client_ip = request.client.host
        current_time = time.time()
        
        self.requests[client_ip] = [
            (ts, count) for ts, count in self.requests[client_ip]
            if current_time - ts < self.window
        ]
        
        request_count = sum(count for _, count in self.requests[client_ip])
        
        if request_count >= self.max_requests:
            logger.warning(
                f"Rate limit excedido para IP {client_ip}: "
                f"{request_count} peticiones en {self.window}s"
            )
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit excedido. Máximo {self.max_requests} peticiones por {self.window} segundos"
            )
        
        self.requests[client_ip].append((current_time, 1))
        response = await call_next(request)
        
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(self.max_requests - request_count - 1)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window))
        
        return response
