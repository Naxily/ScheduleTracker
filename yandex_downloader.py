import os
import requests
from datetime import datetime
import config as cfg

PUBLIC_KEY = "https://disk.yandex.ru/d/g-E9DJTF1kYO2A"
API_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"

def get_excel_files():
    params = {"public_key": PUBLIC_KEY, "limit": 100}
    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return []

    data = response.json()
    items = data.get("_embedded", {}).get("items", [])
    
    excel_files = []
    for item in items:
        name = item.get("name", "")
        if name.lower().endswith(".xlsx"):
            modified_str = item.get("modified", "")
            try:
                modified_dt = datetime.fromisoformat(modified_str.replace('Z', '+00:00'))
            except ValueError:
                modified_dt = datetime.now()
            excel_files.append({
                "name": name,
                "modified": modified_dt,
                "download_url": item.get("file")
            })
    return excel_files

def download_file(file_info, save_dir=None):
    if save_dir is None:
        save_dir = os.path.join(cfg.DOCUMENTS_DIR, "schedules")
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    filepath = os.path.join(save_dir, file_info["name"])
    try:
        response = requests.get(file_info["download_url"], stream=True)
        response.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return filepath
    except Exception as e:
        return None
