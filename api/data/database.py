"""
Gestión de conexión a la base de datos PostgreSQL.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Gestor de conexiones a PostgreSQL con pool de conexiones."""
    
    def __init__(self):
        """Inicializa el gestor de conexiones."""
        self.pool: Optional[SimpleConnectionPool] = None
        
    def initialize_pool(self, minconn: int = None, maxconn: int = None):
        """Inicializa el pool de conexiones a PostgreSQL."""
        if self.pool is not None:
            logger.warning("Pool de conexiones ya inicializado")
            return
        
        minconn = minconn or settings.db_pool_min
        maxconn = maxconn or settings.db_pool_max
        
        try:
            self.pool = SimpleConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                user=settings.db_user,
                password=settings.db_password,
                host=settings.db_host,
                port=settings.db_port,
                database=settings.db_name,
                connect_timeout=settings.db_connect_timeout
            )
            logger.info(f"Pool de conexiones inicializado: {minconn}-{maxconn} conexiones")
        except Exception as e:
            logger.error(f"Error al inicializar pool de conexiones: {e}")
            raise
    
    def close_pool(self):
        """Cierra todas las conexiones del pool."""
        if self.pool is not None:
            self.pool.closeall()
            logger.info("Pool de conexiones cerrado")
            self.pool = None
    
    @contextmanager
    def get_connection(self):
        """Context manager para obtener una conexión del pool."""
        if self.pool is None:
            raise RuntimeError("Pool de conexiones no inicializado. Llame a initialize_pool() primero.")
        
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
        finally:
            if conn is not None:
                self.pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, dict_cursor: bool = True):
        """Context manager para obtener un cursor."""
        with self.get_connection() as conn:
            cursor_factory = RealDictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Error en transacción: {e}")
                raise
            finally:
                cursor.close()
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[tuple] = None,
        fetch: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Ejecuta una query SQL y devuelve los resultados.
        
        Args:
            query: Query SQL a ejecutar
            params: Parámetros de la query (opcional)
            fetch: Si True, devuelve los resultados (SELECT). Si False, solo ejecuta (INSERT/UPDATE)
            
        Returns:
            Lista de diccionarios con los resultados, o None si fetch=False
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            
            if fetch:
                return cursor.fetchall()
            return None
    
    def execute_many(
        self,
        query: str,
        params_list: List[tuple]
    ):
        """
        Ejecuta una query múltiples veces con diferentes parámetros.
        
        Args:
            query: Query SQL a ejecutar
            params_list: Lista de tuplas con parámetros
        """
        with self.get_cursor(dict_cursor=False) as cursor:
            cursor.executemany(query, params_list)
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión a la base de datos.
        
        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            result = self.execute_query("SELECT version();")
            if result:
                logger.info(f"Conexión exitosa a PostgreSQL: {result[0]['version'][:50]}...")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al probar conexión: {e}")
            return False


# Instancia global de la conexión a base de datos (singleton)
db_connection = DatabaseConnection()
