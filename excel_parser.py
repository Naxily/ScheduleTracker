import pandas as pd
import os
import re

def clean_text(text):
    """Оставляет только буквы и цифры, удаляя все пробелы и спецсимволы."""
    return re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9]', '', str(text))

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def find_all_groups(file_path):
    if not os.path.exists(file_path): return []
    try:
        df = pd.read_excel(file_path, header=None, engine='calamine')
    except Exception as e:
        print(f"Ошибка чтения: {e}")
        return []

    groups = set()
    rows, cols = df.shape
    for r in range(rows - 1): 
        for c in range(cols): 
            val = df.iloc[r, c]
            if pd.notna(val):
                text = clean_text(val)
                
                if text in ["Время", "Предмет", "Препод", "Каб", "Преподаватель", "Кабинет", ""] or len(text) > 15:
                    continue
                
                next_row = df.iloc[r + 1]
                has_one = False
                for nv in next_row:
                    if pd.notna(nv):
                        nv_str = str(nv).strip()
                        if nv_str in ["1", "1.0", "1,0"]:
                            has_one = True
                            break
                        try:
                            if float(nv_str.replace(',', '.')) == 1.0:
                                has_one = True
                                break
                        except ValueError:
                            pass
                
                if has_one:
                    groups.add(text)
                    
    return sorted(list(groups), key=natural_sort_key)

def parse_schedule(file_path, group_number):
    if not os.path.exists(file_path): return []
    try:
        df = pd.read_excel(file_path, header=None, engine='calamine')
    except: return []

    rows, cols = df.shape
    for r in range(rows - 1):
        for c in range(cols - 1):
            val = df.iloc[r, c]
            if pd.notna(val):
                cell_text = clean_text(val)
                
                if cell_text == group_number:
                    schedule_data = []
                    for i in range(1, 8):
                        current_row = r + i
                        if current_row >= rows: break
                        
                        try:
                            time_val = df.iloc[current_row, c + 2]
                            subject_val = df.iloc[current_row, c + 3]
                            teacher_val = df.iloc[current_row, c + 4]
                            room_val = df.iloc[current_row, c + 5]
                        except IndexError:
                            continue
                        
                        
                        if pd.notna(time_val):
                            time_str = re.sub(r'\s+', '', str(time_val))
                        else:
                            time_str = ""
                            
                        
                        subject_str = re.sub(r'\s+', ' ', str(subject_val)).strip() if pd.notna(subject_val) else "Нет пары"
                        teacher_str = re.sub(r'\s+', ' ', str(teacher_val)).strip() if pd.notna(teacher_val) else ""
                        room_str = re.sub(r'\s+', ' ', str(room_val)).strip() if pd.notna(room_val) else ""
                        
                        schedule_data.append({
                            "time": time_str, "subject": subject_str, 
                            "teacher": teacher_str, "room": room_str
                        })
                    return schedule_data
    return []
