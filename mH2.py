import requests
import os
import logging
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
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

# Validación de credenciales
if not NOTION_API_KEY or not DATABASE_ID:
    logger.error("Variables de entorno faltantes: NOTION_API_KEY y/o DATABASE_ID_PLANES")
    raise EnvironmentError("Faltan variables de entorno")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}

def validate_api_connection() -> bool:
    try:
        response = requests.get(f"{API_BASE_URL}/databases/{DATABASE_ID}", headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info("Conexión con Notion validada correctamente")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la conexión a Notion: {e}")
        return False

def get_all_pages(page_size: int = 100) -> List[Dict]:
    all_pages, has_more, start_cursor = [], True, None
    while has_more:
        try:
            payload = {"page_size": page_size, "start_cursor": start_cursor} if start_cursor else {"page_size": page_size}
            response = requests.post(f"{API_BASE_URL}/databases/{DATABASE_ID}/query", headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            all_pages.extend(data.get("results", []))
            has_more, start_cursor = data.get("has_more", False), data.get("next_cursor")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener páginas: {e}")
            break
    logger.info(f"Total de páginas obtenidas: {len(all_pages)}")
    return all_pages

def update_page(page_id: str, new_start: datetime, new_end: Optional[datetime]) -> bool:
    url = f"{API_BASE_URL}/pages/{page_id}"
    date_value = {"start": new_start.isoformat(), "end": new_end.isoformat() if new_end else None}
    payload = {"properties": {DATE_PROPERTY_NAME: {"date": date_value}}}
    try:
        response = requests.patch(url, json=payload, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info(f"Página {page_id} actualizada correctamente.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al actualizar {page_id}: {e}")
        return False

def filter_pages_by_formula(pages: List[Dict], formula_filter_value: str, formula_property_name: str) -> List[Dict]:
    filtered_pages = []
    for page in pages:
        formula_property = page.get("properties", {}).get(formula_property_name, {})
        formula_result = formula_property.get("formula", {})
        formula_value = (
            formula_result.get("string") if formula_result.get("type") == "string"
            else str(formula_result.get("number")) if formula_result.get("type") == "number"
            else None
        )
        if formula_value == formula_filter_value:
            filtered_pages.append(page)
    logger.info(f"Páginas que pasaron el filtro de fórmula '{formula_filter_value}': {len(filtered_pages)}")
    return filtered_pages

def adjust_dates(hours: int, start_date: datetime, formula_filter_value: Optional[str] = None, formula_property_name: str = "For - Código de departamento") -> str:
    if not validate_api_connection():
        return "Error: No se pudo conectar a la API de Notion."
    pages = get_all_pages()
    if formula_filter_value:
        pages = filter_pages_by_formula(pages, formula_filter_value, formula_property_name)
    updated, failed, skipped = 0, 0, 0
    for page in pages:
        page_id = page["id"]
        date_info = page.get("properties", {}).get(DATE_PROPERTY_NAME, {}).get("date", {})
        if not date_info or "start" not in date_info:
            skipped += 1
            continue
        try:
            start_date_notion = datetime.fromisoformat(date_info["start"]).replace(tzinfo=None)
            end_date_notion = datetime.fromisoformat(date_info["end"]).replace(tzinfo=None) if date_info.get("end") else None
            if start_date_notion >= start_date:
                new_start = start_date_notion + timedelta(hours=hours)
                new_end = end_date_notion + timedelta(hours=hours) if end_date_notion else None
                if update_page(page_id, new_start, new_end):
                    updated += 1
                else:
                    failed += 1
            else:
                skipped += 1
        except Exception as e:
            logger.error(f"Error procesando página {page_id}: {e}")
            failed += 1
    return f"Actualización completada: {updated} actualizadas, {failed} fallidas, {skipped} omitidas."

