import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Cargar variables de entorno
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_HOR")
DATABASE_ID_PLANES = os.getenv("DATABASE_ID_PLANES")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def get_pages():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID_PLANES}/query"
    response = requests.post(url, headers=HEADERS)
    return response.json().get("results", [])

def update_page(page_id, new_start, new_end):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "Date": {
                "date": {
                    "start": new_start.isoformat(),
                    "end": new_end.isoformat() if new_end else None
                }
            }
        }
    }
    response = requests.patch(url, json=payload, headers=HEADERS)
    return response.status_code, response.json()

def adjust_dates(hours, start_date):
    pages = get_pages()
    updated_pages = 0

    for page in pages:
        properties = page["properties"]
        page_id = page["id"]

        date_info = properties.get("Date", {}).get("date", {})
        if not date_info or "start" not in date_info:
            continue

        start_date_notion = datetime.fromisoformat(date_info["start"]).replace(tzinfo=None)
        end_date_notion = datetime.fromisoformat(date_info["end"]).replace(tzinfo=None) if date_info.get("end") else None

        # Mover solo los horarios que sean iguales o posteriores a start_date
        if start_date_notion >= start_date:
            new_start = start_date_notion + timedelta(hours=hours)
            new_end = end_date_notion + timedelta(hours=hours) if end_date_notion else None

            update_page(page_id, new_start, new_end)
            updated_pages += 1

    return f"Se actualizaron {updated_pages} registros a partir de {start_date.strftime('%Y-%m-%d')}."
