import sqlite3
import os
import re
from datetime import datetime
import config as cfg

DB_PATH = os.path.join(cfg.DOCUMENTS_DIR, "schedule_v3.db")

def natural_sort_key(s):
    """Сортирует строки по-человечески (числа по порядку, а не по алфавиту)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def init_db():
    os.makedirs(cfg.DOCUMENTS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            "group" TEXT,
            time TEXT,
            subject TEXT,
            teacher TEXT,
            room TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_history (
            filename TEXT PRIMARY KEY,
            yandex_modified TEXT,
            local_downloaded TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_schedule(date_str, group_str, schedule_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM schedules WHERE date = ? AND "group" = ?', (date_str, group_str))
    for pair in schedule_data:
        cursor.execute('''
            INSERT INTO schedules (date, "group", time, subject, teacher, room)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (date_str, group_str, pair['time'], pair['subject'], pair['teacher'], pair['room']))
    conn.commit()
    conn.close()

def get_schedule(date_str, group_str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT time, subject, teacher, room FROM schedules 
        WHERE date = ? AND "group" = ? ORDER BY id
    ''', (date_str, group_str))
    rows = cursor.fetchall()
    conn.close()
    return [{"time": r[0], "subject": r[1], "teacher": r[2], "room": r[3]} for r in rows]

def get_all_groups_in_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT "group" FROM schedules')
    rows = cursor.fetchall()
    conn.close()
    
    groups = [r[0] for r in rows]
    return sorted(groups, key=natural_sort_key)

def get_latest_date():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(date) FROM schedules')
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def check_file_needs_update(filename, yandex_modified_dt):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT yandex_modified FROM file_history WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    conn.close()
    if row is None: return True
    return yandex_modified_dt > datetime.fromisoformat(row[0])

def save_file_history(filename, yandex_modified_dt):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO file_history (filename, yandex_modified, local_downloaded)
        VALUES (?, ?, ?)
    ''', (filename, yandex_modified_dt.isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
def get_nearest_date_in_db(target_date_str, group_str):
    """Находит ближайшую дату с расписанием (сначала ищет в будущем, потом в прошлом)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    
    cursor.execute('SELECT MIN(date) FROM schedules WHERE date >= ? AND "group" = ?', (target_date_str, group_str))
    row = cursor.fetchone()
    if row and row[0]:
        conn.close()
        return row[0]
        
    
    cursor.execute('SELECT MAX(date) FROM schedules WHERE date < ? AND "group" = ?', (target_date_str, group_str))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None
