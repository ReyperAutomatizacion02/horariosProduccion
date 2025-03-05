import requests
import os
import logging
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any, Union

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("notion_integration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("notion_integration")

# Cargar variables de entorno
load_dotenv()

# Constantes y configuración
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID_PLANES")
API_BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DATE_PROPERTY_NAME = "Date"
REQUEST_TIMEOUT = 30

# Verifica que las variables de entorno necesarias estén disponibles
if not NOTION_API_KEY or not DATABASE_ID:
    logger.error("Variables de entorno requeridas no encontradas. Verifica NOTION_API_KEY y DATABASE_ID_PLANES.")
    raise EnvironmentError("Variables de entorno requeridas no encontradas")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}

def validate_api_connection() -> bool:
    try:
        url = f"{API_BASE_URL}/databases/{DATABASE_ID}"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info("Conexión a la API de Notion validada correctamente")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al validar la conexión a la API de Notion: {str(e)}")
        return False

def get_database_properties() -> Dict[str, Dict]:
    try:
        url = f"{API_BASE_URL}/databases/{DATABASE_ID}"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        database_info = response.json()
        properties = database_info.get("properties", {})
        
        logger.info(f"Propiedades obtenidas de la base de datos: {', '.join(properties.keys())}")
        return properties
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener propiedades de la base de datos: {str(e)}")
        return {}

def create_filter_condition(property_name: str, property_type: str, value: Any) -> Dict:
    if property_type == "select":
        return {
            "property": property_name,
            "select": {
                "equals": value
            }
        }
    elif property_type == "multi_select":
        return {
            "property": property_name,
            "multi_select": {
                "contains": value
            }
        }
    elif property_type in ["title", "rich_text"]:
        return {
            "property": property_name,
            "rich_text": {
                "contains": value
            }
        }
    elif property_type == "number":
        return {
            "property": property_name,
            "number": {
                "equals": value
            }
        }
    elif property_type == "checkbox":
        return {
            "property": property_name,
            "checkbox": {
                "equals": value
            }
        }
    elif property_type == "people":
        return {
            "property": property_name,
            "people": {
                "contains": value
            }
        }
    elif property_type == "formula":
        return {
            "property": property_name,
            "rich_text": {
                "contains": value
            }
        }
    else:
        logger.warning(f"Tipo de propiedad no soportado para filtrado: {property_type}")
        return {}

def get_pages_with_filter(filters: List[Dict] = None, page_size: int = 100) -> List[Dict]:
    all_pages = []
    has_more = True
    start_cursor = None
    
    while has_more:
        try:
            url = f"{API_BASE_URL}/databases/{DATABASE_ID}/query"
            payload = {
                "page_size": page_size
            }
            
            # Añadir filtros si existen
            if filters and len(filters) > 0:
                if len(filters) == 1:
                    payload["filter"] = filters[0]
                else:
                    payload["filter"] = {
                        "and": filters
                    }
            
            if start_cursor:
                payload["start_cursor"] = start_cursor
                
            response = requests.post(url, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            # Añadir resultados a la lista
            results = data.get("results", [])
            all_pages.extend(results)
            
            # Verificar si hay más páginas
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
            
            logger.info(f"Obtenidas {len(results)} páginas con filtros. Total acumulado: {len(all_pages)}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener páginas de Notion con filtros: {str(e)}")
            break
            
    return all_pages

def update_page(page_id: str, new_start: datetime, new_end: Optional[datetime]) -> Tuple[int, Dict]:
    url = f"{API_BASE_URL}/pages/{page_id}"
    
    # Preparar payload con fecha de inicio y posiblemente fecha de fin
    date_value = {
        "start": new_start.isoformat()
    }
    
    if new_end:
        date_value["end"] = new_end.isoformat()
    
    payload = {
        "properties": {
            DATE_PROPERTY_NAME: {
                "date": date_value
            }
        }
    }
    
    try:
        response = requests.patch(url, json=payload, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info(f"Página {page_id} actualizada correctamente")
        return response.status_code, response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error HTTP al actualizar página {page_id}: {str(e)}")
        return e.response.status_code, e.response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al actualizar página {page_id}: {str(e)}")
        return 500, {"error": str(e)}

def adjust_dates_with_filters(
    hours: int, 
    start_date: datetime, 
    filters: List[Dict[str, Any]] = None
) -> str:
    if not validate_api_connection():
        return "Error: No se pudo conectar a la API de Notion. Verifica tu conexión y credenciales."
    
    # Obtener páginas con los filtros aplicados
    pages = get_pages_with_filter(filters)
    total_pages = len(pages)
    updated_pages = 0
    failed_updates = 0
    skipped_pages = 0
    
    # Construir descripción de filtros para el log
    filter_description = "ninguno"
    if filters and len(filters) > 0:
        filter_props = [f.get("property", "desconocido") for f in filters]
        filter_description = ", ".join(filter_props)
    
    logger.info(f"Iniciando ajuste de fechas: {hours} horas a partir de {start_date.isoformat()}")
    logger.info(f"Filtros aplicados: {filter_description}")
    logger.info(f"Total de páginas a procesar: {total_pages}")
    
    for page in pages:
        properties = page.get("properties", {})
        page_id = page.get("id")
        
        if not page_id:
            logger.warning("Página sin ID encontrada, omitiendo")
            skipped_pages += 1
            continue
            
        # Obtener información de fecha con navegación segura
        date_info = properties.get(DATE_PROPERTY_NAME, {}).get("date", {})
        
        if not date_info or "start" not in date_info:
            logger.info(f"Página {page_id} sin fecha, omitiendo")
            skipped_pages += 1
            continue
            
        try:
            # Conversión a datetime sin zona horaria
            start_date_notion = datetime.fromisoformat(date_info["start"]).replace(tzinfo=None)
            end_date_notion = None
            
            if date_info.get("end"):
                end_date_notion = datetime.fromisoformat(date_info["end"]).replace(tzinfo=None)
                
            # Mover solo los horarios que sean iguales o posteriores a start_date
            if start_date_notion >= start_date:
                new_start = start_date_notion + timedelta(hours=hours)
                new_end = end_date_notion + timedelta(hours=hours) if end_date_notion else None
                
                status_code, _ = update_page(page_id, new_start, new_end)
                
                if 200 <= status_code < 300:
                    updated_pages += 1
                else:
                    failed_updates += 1
            else:
                logger.info(f"Página {page_id} con fecha anterior a {start_date.isoformat()}, omitiendo")
                skipped_pages += 1
                
        except (ValueError, TypeError) as e:
            logger.error(f"Error al procesar fecha de página {page_id}: {str(e)}")
            failed_updates += 1
    
    logger.info(f"Proceso completado: {updated_pages} páginas actualizadas, {failed_updates} fallidas, {skipped_pages} omitidas")
    
    # Crear un mensaje de resumen formateado como string
    resumen = (
        f"Operación completada: Se actualizaron {updated_pages} registros a partir del {start_date.strftime('%Y-%m-%d')}.\n"
        f"Filtros aplicados: {filter_description}\n"
        f"Total de registros filtrados: {total_pages}\n"
        f"Registros actualizados: {updated_pages}\n"
        f"Registros omitidos: {skipped_pages}\n"
        f"Actualizaciones fallidas: {failed_updates}\n"
        f"Ajuste aplicado: {hours} horas"
    )
    
    return resumen

def build_filter_from_properties(property_filters: Dict[str, Any]) -> List[Dict]:
    if not property_filters:
        return []
        
    filters = []
    db_properties = get_database_properties()
    
    for prop_name, prop_value in property_filters.items():
        # Verificar si la propiedad existe en la base de datos
        if prop_name not in db_properties:
            logger.warning(f"Propiedad '{prop_name}' no encontrada en la base de datos, omitiendo filtro")
            continue
            
        # Obtener el tipo de propiedad
        prop_info = db_properties[prop_name]
        prop_type = prop_info.get("type")
        
        # Crear filtro según el tipo de propiedad
        filter_condition = create_filter_condition(prop_name, prop_type, prop_value)
        
        if filter_condition:
            filters.append(filter_condition)
        
    return filters

def adjust_dates_api(
    hours: int, 
    start_date_str: str, 
    property_filters: Dict[str, Any] = None
) -> Dict[str, Any]:
    try:
        # Convertir string a datetime
        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        
        # Construir filtros si se proporcionaron
        filters = build_filter_from_properties(property_filters) if property_filters else None
        
        # Ejecutar el ajuste de fechas con filtros
        result_message = adjust_dates_with_filters(hours, start_date, filters)
        
        # Construir respuesta para API
        return {
            "success": True,
            "message": result_message
        }
        
    except ValueError as e:
        error_msg = f"Formato de fecha inválido: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error al ajustar fechas: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

def list_available_properties() -> List[Dict[str, str]]:
    properties = get_database_properties()
    property_list = []
    
    for name, info in properties.items():
        prop_type = info.get("type", "unknown")
        property_list.append({
            "name": name,
            "type": prop_type
        })
        
    return property_list

# Ejemplo de uso con filtros:
if __name__ == "__main__":
    # Listar propiedades disponibles
    print("Propiedades disponibles en la base de datos:")
    properties = list_available_properties()
    for prop in properties:
        print(f"- {prop['name']} (Tipo: {prop['type']})")
        
    print("\n")
    
    # Ejemplo 1: Ajustar fechas para todas las entradas
    today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    print("Ejemplo 1: Ajustar todas las entradas")
    result1 = adjust_dates_with_filters(hours=2, start_date=today_midnight)
    print(result1)
    
    print("\n")
    
    # Ejemplo 2: Ajustar fechas solo para el cliente "Empresa ABC"
    print("Ejemplo 2: Ajustar solo para un cliente específico")
    filters = build_filter_from_properties({"Cliente": "Empresa ABC"})
    result2 = adjust_dates_with_filters(hours=2, start_date=today_midnight, filters=filters)
    print(result2)
    
    print("\n")
    
    # Ejemplo 3: Ajustar fechas con múltiples filtros
    print("Ejemplo 3: Ajustar con múltiples filtros")
    filters = build_filter_from_properties({
        "Cliente": "Empresa ABC",
        "Usuario": "Juan Pérez"
    })
    result3 = adjust_dates_with_filters(hours=2, start_date=today_midnight, filters=filters)
    print(result3)
