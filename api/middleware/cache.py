"""
Sistema de caché para optimizar respuestas de la API.
"""
from functools import wraps
from typing import Optional, Any, Callable
import hashlib
import json
import time
import logging
from collections import OrderedDict

from ..config import settings

logger = logging.getLogger(__name__)


class LRUCache:
    """Cache LRU (Least Recently Used) thread-safe para respuestas de API."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """Inicializa el caché."""
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.enabled = settings.enable_cache
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Genera una clave única para los argumentos."""
        key_data = {
            'args': args,
            'kwargs': {k: v for k, v in sorted(kwargs.items())}
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor del caché."""
        if not self.enabled:
            return None
        
        if key not in self.cache:
            self.stats['misses'] += 1
            return None
        
        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            self.stats['misses'] += 1
            return None
        
        self.cache.move_to_end(key)
        self.stats['hits'] += 1
        
        return value
    
    def set(self, key: str, value: Any):
        """Almacena un valor en el caché."""
        if not self.enabled:
            return
        
        if key in self.cache:
            self.cache.move_to_end(key)
        
        # Añadir nueva entrada
        self.cache[key] = (value, time.time())
        
        # Si se excede el tamaño, eliminar el más antiguo
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
            self.stats['evictions'] += 1
    
    def clear(self):
        """Limpia el caché completamente."""
        self.cache.clear()
        logger.info("Caché limpiado")
    
    def get_stats(self) -> dict:
        """
        Obtiene estadísticas del caché.
        
        Returns:
            dict: Estadísticas de uso
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'enabled': self.enabled,
            'size': len(self.cache),
            'max_size': self.max_size,
            'ttl': self.ttl,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'evictions': self.stats['evictions'],
            'hit_rate': f"{hit_rate:.2f}%"
        }


# Instancia global del caché
_cache = LRUCache(
    max_size=settings.cache_max_size,
    ttl=settings.cache_ttl
)


def cache_response(ttl: Optional[int] = None):
    """
    Decorador para cachear respuestas de endpoints.
    
    Args:
        ttl: Tiempo de vida personalizado (usa config si None)
        
    Example:
        @app.get("/embalses")
        @cache_response(ttl=3600)
        async def listar_embalses():
            return {"embalses": [...]}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Si el caché está deshabilitado, ejecutar directamente
            if not _cache.enabled:
                return await func(*args, **kwargs)
            
            # Generar clave del caché
            cache_key = _cache._generate_key(func.__name__, *args, **kwargs)
            
            # Intentar obtener del caché
            cached_value = _cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {func.__name__}")
                return cached_value
            
            # Ejecutar función y cachear resultado
            logger.debug(f"Cache MISS: {func.__name__}")
            result = await func(*args, **kwargs)
            _cache.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator


def get_cache_stats() -> dict:
    """Obtiene estadísticas del caché."""
    return _cache.get_stats()


def clear_cache():
    """Limpia el caché."""
    _cache.clear()
