"""
Middleware de seguridad para la API.
"""
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import logging

from ..config import settings

logger = logging.getLogger(__name__)

# Esquema de seguridad para API Key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def api_key_auth(api_key: str = Security(api_key_header)):
    """Valida la API Key en el header de la petición."""
    if not settings.api_keys_list:
        return None
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API Key requerida. Incluya el header X-API-Key"
        )
    
    if api_key not in settings.api_keys_list:
        logger.warning(f"Intento de acceso con API Key inválida: {api_key[:10]}...")
        raise HTTPException(
            status_code=403,
            detail="API Key inválida"
        )
    
    return api_key


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware que añade headers de seguridad a todas las respuestas."""
    
    async def dispatch(self, request: Request, call_next):
        """Procesa la petición y añade headers de seguridad."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Permitir iframes para la previsualización de informes en el frontend
        if "/api/informes/preview/" in str(request.url):
            # Usar una política más permisiva para previsualización
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            # CSP para permitir ser enmarcado por el frontend
            response.headers["Content-Security-Policy"] = "frame-ancestors 'self' http://localhost:3000 http://localhost:3001 http://localhost:8080"
        else:
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Process-Time"] = str(process_time)
        
        if settings.debug:
            logger.debug(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.4f}s"
            )
        
        return response
