import pandas as pd

def dump_grid_to_txt(file_path, output_path="excel_grid_dump.txt"):
    try:
        
        df = pd.read_excel(file_path, header=None, engine='calamine')
    except Exception as e:
        print(f"❌ Ошибка чтения: {e}")
        return

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"--- СЕТКА EXCEL (первые 50 строк x 50 столбцов) ---\n")
        f.write("Нумерация строк и столбцов начинается с 0\n\n")
        
        for r in range(min(50, len(df))):
            row_vals = []
            for c in range(min(50, len(df.columns))):
                val = df.iloc[r, c]
                if pd.notna(val):
                    
                    text = str(val).replace('\n', '/').strip()
                    if len(text) > 10:
                        text = text[:7] + "..."
                    row_vals.append(text)
                else:
                    row_vals.append(".")
            
            
            f.write(f"R{r:02d}: " + " | ".join([f"{v:^8}" for v in row_vals]) + "\n")
            
    print(f"✅ Успешно сохранено в {output_path}")

if __name__ == "__main__":
    dump_grid_to_txt("11.11.2026.xlsx")
