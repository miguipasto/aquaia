"""
Carga y gestión de datos históricos de embalses desde PostgreSQL.
"""
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import logging

from ..config import settings
from .database import db_connection

logger = logging.getLogger(__name__)


class DataLoader:
    """Gestor de datos históricos de embalses desde PostgreSQL."""
    
    def __init__(self):
        """Inicializa el cargador de datos."""
        self._embalses_cache: Optional[List[Dict]] = None
        self._estaciones_cache: Optional[Dict] = None
        
    def initialize(self):
        """
        Inicializa la conexión a la base de datos.
        Debe llamarse al arrancar la aplicación.
        """
        logger.info("Inicializando conexión a base de datos")
        db_connection.initialize_pool(minconn=2, maxconn=10)
        
        if db_connection.test_connection():
            logger.info("Base de datos conectada correctamente")
            self._load_estaciones_cache()
        else:
            raise RuntimeError("No se pudo conectar a la base de datos PostgreSQL")
    
    def close(self):
        """Cierra las conexiones a la base de datos."""
        db_connection.close_pool()
        logger.info("Conexión a base de datos cerrada")
    
    def _load_estaciones_cache(self):
        """Carga información de estaciones en caché."""
        query = """
        SELECT 
            e.codigo_saih,
            e.ubicacion,
            m.nombre as municipio,
            p.nombre as provincia,
            e.coord_x,
            e.coord_y,
            e.id_demarcacion
        FROM estacion_saih e
        LEFT JOIN municipio m ON e.id_municipio = m.id
        LEFT JOIN provincia p ON m.id_provincia = p.id
        ORDER BY e.codigo_saih
        """
        
        results = db_connection.execute_query(query)
        self._estaciones_cache = {row['codigo_saih']: dict(row) for row in results}
        logger.info(f"Caché de estaciones cargada: {len(self._estaciones_cache)} estaciones")
    
    def get_embalses_list(self, fecha_referencia: Optional[str] = None) -> List[Dict]:
        """
        Obtiene la lista de embalses disponibles con información completa.
        
        Args:
            fecha_referencia: Fecha opcional para obtener niveles históricos (YYYY-MM-DD)
        
        Returns:
            Lista de diccionarios con información de cada embalse
        """
        # Si hay fecha de referencia, no usar caché
        if fecha_referencia is None and self._embalses_cache is not None:
            return self._embalses_cache
        
        # Query para obtener embalses con información completa incluyendo último nivel
        if fecha_referencia:
            query = """
            SELECT DISTINCT ON (e.codigo_saih)
                e.codigo_saih,
                e.ubicacion,
                m.nombre as municipio,
                p.nombre as provincia,
                ca.nombre as comunidad_autonoma,
                d.nombre as demarcacion,
                og.nombre as organismo_gestor,
                og.tipo_gestion,
                e.coord_x,
                e.coord_y,
                e.nivel_maximo,
                sne.nivel as ultimo_nivel,
                sne.fecha as fecha_ultimo_registro
            FROM estacion_saih e
            INNER JOIN saih_nivel_embalse sne ON e.codigo_saih = sne.codigo_saih
            LEFT JOIN municipio m ON e.id_municipio = m.id
            LEFT JOIN provincia p ON m.id_provincia = p.id
            LEFT JOIN comunidad_autonoma ca ON p.id_ccaa = ca.id
            LEFT JOIN demarcacion d ON e.id_demarcacion = d.id
            LEFT JOIN organismo_gestor og ON d.id_gestor = og.id
            WHERE sne.fecha <= %s
            ORDER BY e.codigo_saih, sne.fecha DESC
            """
            results = db_connection.execute_query(query, (fecha_referencia,))
        else:
            query = """
            SELECT DISTINCT ON (e.codigo_saih)
                e.codigo_saih,
                e.ubicacion,
                m.nombre as municipio,
                p.nombre as provincia,
                ca.nombre as comunidad_autonoma,
                d.nombre as demarcacion,
                og.nombre as organismo_gestor,
                og.tipo_gestion,
                e.coord_x,
                e.coord_y,
                e.nivel_maximo,
                sne.nivel as ultimo_nivel,
                sne.fecha as fecha_ultimo_registro
            FROM estacion_saih e
            INNER JOIN saih_nivel_embalse sne ON e.codigo_saih = sne.codigo_saih
            LEFT JOIN municipio m ON e.id_municipio = m.id
            LEFT JOIN provincia p ON m.id_provincia = p.id
            LEFT JOIN comunidad_autonoma ca ON p.id_ccaa = ca.id
            LEFT JOIN demarcacion d ON e.id_demarcacion = d.id
            LEFT JOIN organismo_gestor og ON d.id_gestor = og.id
            ORDER BY e.codigo_saih, sne.fecha DESC
            """
            results = db_connection.execute_query(query)
        
        embalses_list = [
            {
                'codigo_saih': row['codigo_saih'],
                'ubicacion': row['ubicacion'],
                'municipio': row['municipio'],
                'provincia': row['provincia'],
                'comunidad_autonoma': row['comunidad_autonoma'],
                'demarcacion': row['demarcacion'],
                'organismo_gestor': row['organismo_gestor'],
                'tipo_gestion': row['tipo_gestion'],
                'coord_x': float(row['coord_x']) if row['coord_x'] is not None else None,
                'coord_y': float(row['coord_y']) if row['coord_y'] is not None else None,
                'nivel_maximo': float(row['nivel_maximo']) if row['nivel_maximo'] is not None else None,
                'ultimo_nivel': float(row['ultimo_nivel']) if row['ultimo_nivel'] is not None else 0.0,
                'fecha_ultimo_registro': row['fecha_ultimo_registro'].strftime('%Y-%m-%d') if row['fecha_ultimo_registro'] is not None else None
            }
            for row in results
        ]
        
        # Solo cachear si no hay fecha de referencia
        if fecha_referencia is None:
            self._embalses_cache = embalses_list
        
        logger.info(f"Lista de embalses obtenida: {len(embalses_list)} embalses")
        return embalses_list
    
    def get_embalse_data(self, codigo_saih: str) -> pd.DataFrame:
        """
        Obtiene todos los datos históricos de un embalse específico.
        
        Args:
            codigo_saih: Código del embalse
            
        Returns:
            DataFrame con los datos del embalse (nivel, precipitación, temperatura, caudal)
            
        Raises:
            ValueError: Si el embalse no existe
        """
        # Verificar que el embalse existe
        if not self.embalse_exists(codigo_saih):
            raise ValueError(f"Embalse {codigo_saih} no encontrado en la base de datos")
        
        # Query que hace join de todas las mediciones
        query = """
        SELECT 
            n.fecha,
            n.nivel,
            p.precipitacion,
            t.temperatura,
            AVG(c.caudal) as caudal_promedio
        FROM saih_nivel_embalse n
        LEFT JOIN saih_precipitacion p 
            ON n.codigo_saih = p.codigo_saih AND n.fecha = p.fecha
        LEFT JOIN saih_temperatura t 
            ON n.codigo_saih = t.codigo_saih AND n.fecha = t.fecha
        LEFT JOIN saih_caudal c 
            ON n.codigo_saih = c.codigo_saih AND n.fecha = c.fecha
        WHERE n.codigo_saih = %s
        GROUP BY n.fecha, n.nivel, p.precipitacion, t.temperatura
        ORDER BY n.fecha
        """
        
        results = db_connection.execute_query(query, (codigo_saih,))
        
        # Convertir a DataFrame
        df = pd.DataFrame(results)
        
        if len(df) == 0:
            raise ValueError(f"No hay datos para el embalse {codigo_saih}")
        
        # Convertir fecha a datetime
        df['fecha'] = pd.to_datetime(df['fecha'])
        
        # Añadir codigo_saih y provincia para compatibilidad con código existente
        df['codigo_saih'] = codigo_saih
        if self._estaciones_cache and codigo_saih in self._estaciones_cache:
            df['provincia'] = self._estaciones_cache[codigo_saih]['provincia']
        
        return df.sort_values('fecha')

    def get_embalse_actual(self, codigo_saih: str, fecha: Optional[str] = None):
        """
        Obtiene el estado actual (o en una fecha dada) de un embalse.
        
        Args:
            codigo_saih: Código del embalse
            fecha: Fecha de consulta (YYYY-MM-DD), opcional
            
        Returns:
            Objeto con nombre, nivel_actual, capacidad_total y fecha o None
        """
        query = """
        SELECT 
            e.ubicacion as nombre,
            n.nivel as nivel_actual,
            e.nivel_maximo as capacidad_total,
            n.fecha
        FROM estacion_saih e
        JOIN saih_nivel_embalse n ON e.codigo_saih = n.codigo_saih
        WHERE e.codigo_saih = %s
        """
        
        params = [codigo_saih]
        if fecha:
            query += " AND n.fecha <= %s"
            params.append(fecha)
            
        query += " ORDER BY n.fecha DESC LIMIT 1"
        
        results = db_connection.execute_query(query, tuple(params))
        
        if not results:
            return None
            
        from types import SimpleNamespace
        return SimpleNamespace(**results[0])

    def get_historico(
        self, 
        codigo_saih: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Obtiene serie histórica de un embalse con filtros opcionales de fecha.
        
        Args:
            codigo_saih: Código del embalse
            start_date: Fecha inicial (YYYY-MM-DD), opcional
            end_date: Fecha final (YYYY-MM-DD), opcional
            
        Returns:
            DataFrame filtrado
        """
        # Construir query con filtros opcionales
        query = """
        SELECT 
            n.fecha,
            n.nivel,
            p.precipitacion,
            t.temperatura,
            AVG(c.caudal) as caudal_promedio
        FROM saih_nivel_embalse n
        LEFT JOIN saih_precipitacion p 
            ON n.codigo_saih = p.codigo_saih AND n.fecha = p.fecha
        LEFT JOIN saih_temperatura t 
            ON n.codigo_saih = t.codigo_saih AND n.fecha = t.fecha
        LEFT JOIN saih_caudal c 
            ON n.codigo_saih = c.codigo_saih AND n.fecha = c.fecha
        WHERE n.codigo_saih = %s
        """
        
        params = [codigo_saih]
        
        if start_date:
            query += " AND n.fecha >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND n.fecha <= %s"
            params.append(end_date)
        
        query += """
        GROUP BY n.fecha, n.nivel, p.precipitacion, t.temperatura
        ORDER BY n.fecha
        """
        
        results = db_connection.execute_query(query, tuple(params))
        df = pd.DataFrame(results)
        
        if len(df) > 0:
            df['fecha'] = pd.to_datetime(df['fecha'])
        
        return df
    
    def get_resumen(self, codigo_saih: str) -> Dict:
        """
        Obtiene un resumen estadístico del embalse.
        
        Args:
            codigo_saih: Código del embalse
            
        Returns:
            Diccionario con estadísticas básicas
        """
        # Query optimizada para obtener resumen
        query = """
        WITH ultimo_registro AS (
            SELECT fecha, nivel
            FROM saih_nivel_embalse
            WHERE codigo_saih = %s
            ORDER BY fecha DESC
            LIMIT 1
        ),
        estadisticas_anuales AS (
            SELECT 
                AVG(nivel) as nivel_medio_anual,
                MIN(nivel) as nivel_min_anual,
                MAX(nivel) as nivel_max_anual
            FROM saih_nivel_embalse
            WHERE codigo_saih = %s
                AND fecha >= (SELECT fecha FROM ultimo_registro) - INTERVAL '365 days'
        )
        SELECT 
            u.fecha as fecha_ultimo_registro,
            u.nivel as ultimo_nivel,
            e.nivel_medio_anual,
            e.nivel_min_anual,
            e.nivel_max_anual
        FROM ultimo_registro u
        CROSS JOIN estadisticas_anuales e
        """
        
        results = db_connection.execute_query(query, (codigo_saih, codigo_saih))
        
        if not results or len(results) == 0:
            raise ValueError(f"No hay datos para el embalse {codigo_saih}")
        
        row = results[0]
        
        return {
            'codigo_saih': codigo_saih,
            'ultimo_nivel': float(row['ultimo_nivel']) if row['ultimo_nivel'] is not None else None,
            'fecha_ultimo_registro': row['fecha_ultimo_registro'].strftime('%Y-%m-%d') if row['fecha_ultimo_registro'] else None,
            'nivel_medio_anual': float(row['nivel_medio_anual']) if row['nivel_medio_anual'] is not None else None,
            'nivel_min_anual': float(row['nivel_min_anual']) if row['nivel_min_anual'] is not None else None,
            'nivel_max_anual': float(row['nivel_max_anual']) if row['nivel_max_anual'] is not None else None
        }
    
    def embalse_exists(self, codigo_saih: str) -> bool:
        """
        Verifica si un embalse existe en la base de datos.
        
        Args:
            codigo_saih: Código del embalse
            
        Returns:
            True si existe, False si no
        """
        query = """
        SELECT EXISTS(
            SELECT 1 FROM estacion_saih WHERE codigo_saih = %s
        ) as exists
        """
        
        result = db_connection.execute_query(query, (codigo_saih,))
        return result[0]['exists'] if result else False
    
    def get_fecha_maxima(self, codigo_saih: str) -> str:
        """
        Obtiene la fecha máxima disponible para un embalse.
        
        Args:
            codigo_saih: Código del embalse
            
        Returns:
            Fecha en formato YYYY-MM-DD
        """
        query = """
        SELECT MAX(fecha) as fecha_max
        FROM saih_nivel_embalse
        WHERE codigo_saih = %s
        """
        
        result = db_connection.execute_query(query, (codigo_saih,))
        
        if result and result[0]['fecha_max']:
            return result[0]['fecha_max'].strftime('%Y-%m-%d')
        
        raise ValueError(f"No hay datos para el embalse {codigo_saih}")
    
    def get_demarcaciones(self) -> List[Dict]:
        """
        Obtiene lista de todas las demarcaciones hidrográficas.
        
        Returns:
            Lista de diccionarios con información de demarcaciones
        """
        query = """
        SELECT 
            d.id,
            d.nombre,
            og.nombre as organismo_gestor,
            og.tipo_gestion,
            STRING_AGG(DISTINCT ca.nombre, ', ' ORDER BY ca.nombre) as comunidades,
            COUNT(DISTINCT e.codigo_saih) as num_embalses
        FROM demarcacion d
        JOIN organismo_gestor og ON d.id_gestor = og.id
        LEFT JOIN demarcacion_ccaa dc ON d.id = dc.id_demarcacion
        LEFT JOIN comunidad_autonoma ca ON dc.id_ccaa = ca.id
        LEFT JOIN estacion_saih e ON d.id = e.id_demarcacion
        GROUP BY d.id, d.nombre, og.nombre, og.tipo_gestion
        ORDER BY d.nombre
        """
        
        results = db_connection.execute_query(query)
        
        return [
            {
                'id': row['id'],
                'nombre': row['nombre'],
                'organismo_gestor': row['organismo_gestor'],
                'tipo_gestion': row['tipo_gestion'],
                'comunidades': row['comunidades'].split(', ') if row['comunidades'] else [],
                'num_embalses': int(row['num_embalses'])
            }
            for row in results
        ]
    
    def get_demarcacion_detail(self, id_demarcacion: str) -> Dict:
        """
        Obtiene información detallada de una demarcación.
        
        Args:
            id_demarcacion: ID de la demarcación
            
        Returns:
            Diccionario con información completa
        """
        query = """
        SELECT 
            d.id,
            d.nombre,
            og.nombre as organismo_gestor,
            og.tipo_gestion,
            STRING_AGG(DISTINCT ca.nombre, ', ' ORDER BY ca.nombre) as comunidades,
            COUNT(DISTINCT e.codigo_saih) as num_embalses
        FROM demarcacion d
        JOIN organismo_gestor og ON d.id_gestor = og.id
        LEFT JOIN demarcacion_ccaa dc ON d.id = dc.id_demarcacion
        LEFT JOIN comunidad_autonoma ca ON dc.id_ccaa = ca.id
        LEFT JOIN estacion_saih e ON d.id = e.id_demarcacion
        WHERE d.id = %s
        GROUP BY d.id, d.nombre, og.nombre, og.tipo_gestion
        """
        
        results = db_connection.execute_query(query, (id_demarcacion,))
        
        if not results:
            return None
        
        row = results[0]
        return {
            'id': row['id'],
            'nombre': row['nombre'],
            'organismo_gestor': row['organismo_gestor'],
            'tipo_gestion': row['tipo_gestion'],
            'comunidades': row['comunidades'].split(', ') if row['comunidades'] else [],
            'num_embalses': int(row['num_embalses'])
        }
    
    def get_embalses_by_demarcacion(self, id_demarcacion: str) -> List[str]:
        """
        Obtiene códigos de embalses en una demarcación.
        
        Args:
            id_demarcacion: ID de la demarcación
            
        Returns:
            Lista de códigos SAIH
        """
        query = """
        SELECT codigo_saih, ubicacion
        FROM estacion_saih
        WHERE id_demarcacion = %s
        ORDER BY ubicacion
        """
        
        results = db_connection.execute_query(query, (id_demarcacion,))
        
        return [
            {'codigo_saih': row['codigo_saih'], 'ubicacion': row['ubicacion']}
            for row in results
        ]
    
    def get_organismos(self) -> List[Dict]:
        """
        Obtiene lista de organismos gestores.
        
        Returns:
            Lista de organismos con sus demarcaciones
        """
        query = """
        SELECT 
            og.id,
            og.nombre,
            og.tipo_gestion,
            COUNT(DISTINCT d.id) as num_demarcaciones
        FROM organismo_gestor og
        LEFT JOIN demarcacion d ON og.id = d.id_gestor
        GROUP BY og.id, og.nombre, og.tipo_gestion
        ORDER BY og.nombre
        """
        
        results = db_connection.execute_query(query)
        
        return [
            {
                'id': int(row['id']),
                'nombre': row['nombre'],
                'tipo_gestion': row['tipo_gestion'],
                'num_demarcaciones': int(row['num_demarcaciones'])
            }
            for row in results
        ]
    
    def get_comunidades_autonomas(self) -> List[Dict]:
        """Obtiene lista de comunidades autónomas con número de embalses."""
        query = """
        SELECT 
            ca.id,
            ca.nombre,
            COUNT(DISTINCT e.codigo_saih) as num_embalses
        FROM comunidad_autonoma ca
        LEFT JOIN provincia p ON ca.id = p.id_ccaa
        LEFT JOIN municipio m ON p.id = m.id_provincia
        LEFT JOIN estacion_saih e ON m.id = e.id_municipio
        GROUP BY ca.id, ca.nombre
        ORDER BY ca.nombre
        """
        
        results = db_connection.execute_query(query)
        
        return [
            {
                'id': int(row['id']),
                'nombre': row['nombre'],
                'tipo': 'ccaa',
                'padre': None,
                'num_embalses': int(row['num_embalses'])
            }
            for row in results
        ]
    
    def get_provincias(self, id_ccaa: Optional[int] = None) -> List[Dict]:
        """Obtiene lista de provincias, opcionalmente filtradas por CCAA."""
        query = """
        SELECT 
            p.id,
            p.nombre,
            ca.nombre as ccaa,
            COUNT(DISTINCT e.codigo_saih) as num_embalses
        FROM provincia p
        JOIN comunidad_autonoma ca ON p.id_ccaa = ca.id
        LEFT JOIN municipio m ON p.id = m.id_provincia
        LEFT JOIN estacion_saih e ON m.id = e.id_municipio
        """
        
        params = []
        if id_ccaa is not None:
            query += " WHERE p.id_ccaa = %s"
            params.append(id_ccaa)
        
        query += " GROUP BY p.id, p.nombre, ca.nombre ORDER BY p.nombre"
        
        results = db_connection.execute_query(query, tuple(params) if params else None)
        
        return [
            {
                'id': int(row['id']),
                'nombre': row['nombre'],
                'tipo': 'provincia',
                'padre': row['ccaa'],
                'num_embalses': int(row['num_embalses'])
            }
            for row in results
        ]
    
    def get_estadisticas_region(self, region_tipo: str, region_id: int) -> Dict:
        """
        Calcula estadísticas agregadas para una región geográfica.
        
        Args:
            region_tipo: 'ccaa', 'provincia' o 'demarcacion'
            region_id: ID de la región
            
        Returns:
            Diccionario con estadísticas agregadas
        """
        # Construir query según tipo de región
        if region_tipo == 'ccaa':
            join_condition = """
                JOIN municipio mu ON e.id_municipio = mu.id
                JOIN provincia p ON mu.id_provincia = p.id
                WHERE p.id_ccaa = %s
            """
            region_name_query = "SELECT nombre FROM comunidad_autonoma WHERE id = %s"
        elif region_tipo == 'provincia':
            join_condition = """
                JOIN municipio mu ON e.id_municipio = mu.id
                WHERE mu.id_provincia = %s
            """
            region_name_query = "SELECT nombre FROM provincia WHERE id = %s"
        elif region_tipo == 'demarcacion':
            join_condition = "WHERE e.id_demarcacion = %s"
            region_name_query = "SELECT nombre FROM demarcacion WHERE id = %s"
        else:
            raise ValueError(f"Tipo de región no válido: {region_tipo}")
        
        # Obtener nombre de la región
        region_result = db_connection.execute_query(region_name_query, (region_id,))
        if not region_result:
            return None
        
        region_nombre = region_result[0]['nombre']
        
        # Query de estadísticas
        query = f"""
        WITH ultimos_niveles AS (
            SELECT DISTINCT ON (n.codigo_saih)
                n.codigo_saih,
                n.nivel,
                n.fecha,
                e.nivel_maximo
            FROM saih_nivel_embalse n
            JOIN estacion_saih e ON n.codigo_saih = e.codigo_saih
            {join_condition}
            ORDER BY n.codigo_saih, n.fecha DESC
        )
        SELECT 
            COUNT(*) as num_embalses,
            SUM(nivel) as nivel_total_actual,
            SUM(nivel_maximo) as capacidad_total,
            AVG(CASE WHEN nivel_maximo > 0 THEN (nivel / nivel_maximo * 100) ELSE NULL END) as porcentaje_llenado,
            AVG(nivel) as nivel_promedio,
            MIN(nivel) as nivel_min,
            MAX(nivel) as nivel_max,
            MAX(fecha) as ultima_actualizacion
        FROM ultimos_niveles
        """
        
        results = db_connection.execute_query(query, (region_id,))
        
        if not results or results[0]['num_embalses'] == 0:
            return None
        
        row = results[0]
        return {
            'region_nombre': region_nombre,
            'region_tipo': region_tipo,
            'num_embalses': int(row['num_embalses']),
            'nivel_total_actual': float(row['nivel_total_actual']) if row['nivel_total_actual'] else 0.0,
            'capacidad_total': float(row['capacidad_total']) if row['capacidad_total'] else 0.0,
            'porcentaje_llenado': float(row['porcentaje_llenado']) if row['porcentaje_llenado'] else 0.0,
            'nivel_promedio': float(row['nivel_promedio']) if row['nivel_promedio'] else 0.0,
            'nivel_min': float(row['nivel_min']) if row['nivel_min'] else 0.0,
            'nivel_max': float(row['nivel_max']) if row['nivel_max'] else 0.0,
            'ultima_actualizacion': row['ultima_actualizacion'].strftime('%Y-%m-%d') if row['ultima_actualizacion'] else None
        }
    
    def comparar_embalses(self, codigos_saih: List[str]) -> Dict:
        """
        Compara niveles actuales y tendencias de múltiples embalses.
        
        Args:
            codigos_saih: Lista de códigos de embalses a comparar
            
        Returns:
            Diccionario con datos de comparación
        """
        from datetime import date as date_class
        
        placeholders = ','.join(['%s'] * len(codigos_saih))
        
        query = f"""
        WITH nivel_actual AS (
            SELECT DISTINCT ON (codigo_saih)
                codigo_saih,
                nivel as nivel_actual,
                fecha as fecha_actual
            FROM saih_nivel_embalse
            WHERE codigo_saih IN ({placeholders})
            ORDER BY codigo_saih, fecha DESC
        ),
        nivel_30d AS (
            SELECT DISTINCT ON (codigo_saih)
                codigo_saih,
                nivel as nivel_30d
            FROM saih_nivel_embalse
            WHERE codigo_saih IN ({placeholders})
              AND fecha <= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY codigo_saih, fecha DESC
        ),
        nivel_90d AS (
            SELECT DISTINCT ON (codigo_saih)
                codigo_saih,
                nivel as nivel_90d
            FROM saih_nivel_embalse
            WHERE codigo_saih IN ({placeholders})
              AND fecha <= CURRENT_DATE - INTERVAL '90 days'
            ORDER BY codigo_saih, fecha DESC
        )
        SELECT 
            e.codigo_saih,
            e.ubicacion,
            na.nivel_actual,
            na.fecha_actual,
            n30.nivel_30d,
            n90.nivel_90d,
            e.nivel_maximo,
            (na.nivel_actual - n30.nivel_30d) as var_30d,
            (na.nivel_actual - n90.nivel_90d) as var_90d
        FROM estacion_saih e
        JOIN nivel_actual na ON e.codigo_saih = na.codigo_saih
        LEFT JOIN nivel_30d n30 ON e.codigo_saih = n30.codigo_saih
        LEFT JOIN nivel_90d n90 ON e.codigo_saih = n90.codigo_saih
        WHERE e.codigo_saih IN ({placeholders})
        ORDER BY e.ubicacion
        """
        
        params = codigos_saih * 4  # Repetir parámetros para cada CTE
        results = db_connection.execute_query(query, tuple(params))
        
        embalses_comp = []
        for row in results:
            # Determinar tendencia
            var_30d = float(row['var_30d']) if row['var_30d'] is not None else 0
            if abs(var_30d) < 1.0:
                tendencia = 'estable'
            elif var_30d > 0:
                tendencia = 'subiendo'
            else:
                tendencia = 'bajando'
            
            porcentaje = None
            if row['nivel_maximo'] and row['nivel_maximo'] > 0:
                porcentaje = (float(row['nivel_actual']) / float(row['nivel_maximo'])) * 100
            
            embalses_comp.append({
                'codigo_saih': row['codigo_saih'],
                'ubicacion': row['ubicacion'],
                'nivel_actual': float(row['nivel_actual']),
                'nivel_hace_30d': float(row['nivel_30d']) if row['nivel_30d'] is not None else None,
                'nivel_hace_90d': float(row['nivel_90d']) if row['nivel_90d'] is not None else None,
                'variacion_30d': var_30d,
                'variacion_90d': float(row['var_90d']) if row['var_90d'] is not None else None,
                'porcentaje_capacidad': porcentaje,
                'tendencia': tendencia
            })
        
        # Calcular resumen
        niveles = [e['nivel_actual'] for e in embalses_comp]
        resumen = {
            'total_embalses': len(embalses_comp),
            'nivel_promedio': sum(niveles) / len(niveles) if niveles else 0,
            'nivel_min': min(niveles) if niveles else 0,
            'nivel_max': max(niveles) if niveles else 0,
            'subiendo': sum(1 for e in embalses_comp if e['tendencia'] == 'subiendo'),
            'bajando': sum(1 for e in embalses_comp if e['tendencia'] == 'bajando'),
            'estable': sum(1 for e in embalses_comp if e['tendencia'] == 'estable')
        }
        
        fecha_consulta = results[0]['fecha_actual'].strftime('%Y-%m-%d') if results and results[0]['fecha_actual'] else date_class.today().strftime('%Y-%m-%d')
        
        return {
            'fecha_consulta': fecha_consulta,
            'embalses': embalses_comp,
            'resumen': resumen
        }

# Instancia global del data loader (singleton)
data_loader = DataLoader()
