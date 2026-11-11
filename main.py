import flet as ft
import os
import webbrowser
import threading
from datetime import datetime, date, timedelta

import yandex_downloader as yd
import excel_parser as ep
import database as db
import config as cfg

YANDEX_URL = "https://disk.yandex.ru/d/g-E9DJTF1kYO2A"

def extract_date_from_filename(filename):
    base_name = os.path.splitext(filename)[0].strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d-%m-%Y", "%d-%m-%y"):
        try: 
            return datetime.strptime(base_name, fmt).date()
        except ValueError: 
            continue
    return None

def main(page: ft.Page):
    page.title = "Schedule Tracker"
    config = cfg.load_config()
    page.theme_mode = ft.ThemeMode.DARK if config.get("theme") == "dark" else ft.ThemeMode.LIGHT
    page.padding = 20
    page.window_width = 600 
    page.window_height = 800

    db.init_db()
    
    current_view_date = date.today()

    def clean_old_files():
        if not config.get("cleanup_enabled", True): return
        schedules_dir = os.path.join(cfg.DOCUMENTS_DIR, "schedules")
        if not os.path.exists(schedules_dir): return
        
        files = [f for f in os.listdir(schedules_dir) if f.endswith(".xlsx")]
        if len(files) > 30:
            files.sort(key=lambda x: os.path.getmtime(os.path.join(schedules_dir, x)))
            for i in range(len(files) - 30):
                os.remove(os.path.join(schedules_dir, files[i]))
            print(f"🧹 Очищено {len(files) - 30} старых файлов.")

    def process_local_files():
        print("\n--- СКАНИРОВАНИЕ ЛОКАЛЬНОЙ ПАПКИ ---")
        schedules_dir = os.path.join(cfg.DOCUMENTS_DIR, "schedules")
        if not os.path.exists(schedules_dir): return

        files = [f for f in os.listdir(schedules_dir) if f.lower().endswith(".xlsx")]
        for filename in files:
            filepath = os.path.join(schedules_dir, filename)
            db_date_obj = extract_date_from_filename(filename)
            
            if db_date_obj:
                db_date = db_date_obj.strftime("%Y-%m-%d")
                print(f"📂 Обработка локального файла: {filename} -> Дата: {db_date}")
                all_groups = ep.find_all_groups(filepath)
                for grp in all_groups:
                    parsed_data = ep.parse_schedule(filepath, grp)
                    if parsed_data:
                        db.save_schedule(db_date, grp, parsed_data)
            else:
                print(f"⚠️ Пропущен файл (не распознана дата): {filename}")

    def do_sync(callback_on_finish, force_latest=False):
        try:
            print("\n--- СИНХРОНИЗАЦИЯ С ЯНДЕКС.ДИСКОМ ---")
            files = yd.get_excel_files()
            if files:
                files.sort(key=lambda x: x['modified'], reverse=True)
                
                for idx, f in enumerate(files):
                    is_latest = (idx == 0)
                    local_filepath = os.path.join(cfg.DOCUMENTS_DIR, "schedules", f['name'])
                    needs_update = db.check_file_needs_update(f['name'], f['modified'])
                    
                    if (force_latest and is_latest) or needs_update or not os.path.exists(local_filepath):
                        print(f"⬇️ Скачиваем: {f['name']}")
                        filepath = yd.download_file(f)
                        if not filepath: continue
                        
                        db_date_obj = extract_date_from_filename(f['name'])
                        if db_date_obj:
                            db_date = db_date_obj.strftime("%Y-%m-%d")
                            all_groups = ep.find_all_groups(filepath)
                            for grp in all_groups:
                                parsed_data = ep.parse_schedule(filepath, grp)
                                if parsed_data:
                                    db.save_schedule(db_date, grp, parsed_data)
                            
                        db.save_file_history(f['name'], f['modified'])
            
            process_local_files()
            clean_old_files()
            
        except Exception as e:
            print("❌ Ошибка синхронизации:", e)
        finally:
            callback_on_finish()

    def show_startup_loading():
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        
        loading_ring = ft.ProgressRing(width=60, height=60, stroke_width=5, color=ft.Colors.BLUE_400)
        loading_text = ft.Text("Проверка актуальности расписания...", size=18, color=ft.Colors.GREY_400)
        
        page.add(ft.Column([loading_ring, loading_text], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        page.update()

        async def finish_loading():
            nonlocal current_view_date
            groups_in_db = db.get_all_groups_in_db()
            saved_group = config.get("group")
            
            if saved_group and saved_group in groups_in_db:
                
                now = datetime.now()
                target_date = date.today()
                
                
                if now.hour >= 20:
                    target_date += timedelta(days=1)
                
                target_str = target_date.strftime("%Y-%m-%d")
                schedule = db.get_schedule(target_str, saved_group)
                
                if schedule:
                    current_view_date = target_date
                else:
                    
                    nearest_str = db.get_nearest_date_in_db(target_str, saved_group)
                    if nearest_str:
                        current_view_date = datetime.strptime(nearest_str, "%Y-%m-%d").date()
                    else:
                        current_view_date = target_date
                
                show_main_screen()
            else:
                show_startup_screen()

        def bg_task():
            do_sync(callback_on_finish=lambda: page.run_task(finish_loading), force_latest=True)
        threading.Thread(target=bg_task, daemon=True).start()

    def show_startup_screen():
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START
        page.scroll = ft.ScrollMode.AUTO
        
        groups_list = db.get_all_groups_in_db()
        if not groups_list: groups_list = ["469"]
        current_group = config["group"] if config.get("group") in groups_list else groups_list[0]

        def save_and_continue(new_group):
            config["group"] = str(new_group).strip()
            cfg.save_config(config)
            print(f"✅ Группа {config['group']} сохранена в config.json")
            show_main_screen()

        def on_continue(e):
            new_group = group_input.value.strip()
            if not new_group: new_group = current_group
            save_and_continue(new_group)

        group_input = ft.TextField(
            label="Или введите вручную", 
            value=current_group, 
            width=250, 
            text_align=ft.TextAlign.CENTER,
            on_submit=on_continue
        )

        def open_group_dialog(e):
            def select_group(selected_group):
                group_dialog.open = False
                page.update()
                save_and_continue(selected_group)

            buttons = []
            for g in groups_list:
                buttons.append(
                    ft.Button(
                        g,
                        on_click=lambda e, grp=g: select_group(grp),
                        width=110,
                        height=45,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=5,
                            text_style=ft.TextStyle(size=13, weight=ft.FontWeight.BOLD)
                        )
                    )
                )

            wrap_grid = ft.Row(
                wrap=True,
                spacing=10,
                run_spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=buttons
            )

            group_dialog = ft.AlertDialog(
                title=ft.Text("Выберите группу", text_align=ft.TextAlign.CENTER),
                content=ft.Container(content=wrap_grid, width=500, padding=10),
                modal=False,
                shape=ft.RoundedRectangleBorder(radius=15),
            )
            if group_dialog not in page.overlay:
                page.overlay.append(group_dialog)
            group_dialog.open = True
            page.update()

        page.add(
            ft.Column([
                ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                
                ft.Image(src="assets/icons/logo1.png", width=300, height=120, fit=ft.BoxFit.CONTAIN),
                
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                
                ft.Text("Приветствую!", size=36, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Text("Какая ваша группа?", size=20, color=ft.Colors.GREY_400),
                ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                ft.Button(
                    "Выбрать из списка", 
                    on_click=open_group_dialog, 
                    width=280, height=50,
                    bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                group_input,
                ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                ft.Button(
                    "Продолжить", on_click=on_continue, width=280, height=50, 
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                )
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        page.update()

    def show_main_screen():
        page.clean()
        
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START
        page.scroll = ft.ScrollMode.ADAPTIVE
        
        def refresh_data(e=None):
            btn_refresh.disabled = True
            status_text.value = "⏳ Обновление..."
            page.update()

            async def finish_refresh_ui():
                btn_refresh.disabled = False
                status_text.value = "✅ Обновлено"
                show_schedule_for_date(current_view_date)
                page.update()

            def bg_task():
                do_sync(callback_on_finish=lambda: page.run_task(finish_refresh_ui), force_latest=True)
            threading.Thread(target=bg_task, daemon=True).start()

        def get_btn_style(btn_date):
            is_active = (current_view_date == btn_date)
            return ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=ft.Colors.BLUE_600 if is_active else ft.Colors.SURFACE_CONTAINER_HIGHEST,
                color=ft.Colors.WHITE if is_active else ft.Colors.ON_SURFACE
            )

        def show_schedule_for_date(target_date):
            nonlocal current_view_date
            schedule_list.controls.clear()
            db_date_str = target_date.strftime("%Y-%m-%d")
            schedule = db.get_schedule(db_date_str, config["group"])
            
            header_date.value = target_date.strftime("%d.%m.%Y")
            
            today = date.today()
            btn_yesterday.style = get_btn_style(today - timedelta(days=1))
            btn_today.style = get_btn_style(today)
            btn_tomorrow.style = get_btn_style(today + timedelta(days=1))
            
            if not schedule:
                schedule_list.controls.append(
                    ft.Text(f"На этот день расписания нет (Группа {config['group']}).", 
                            size=18, color=ft.Colors.RED_400, italic=True)
                )
            else:
                for pair in schedule:
                    is_empty = (pair['subject'] == "Нет пары")
                    bg_color = ft.Colors.SURFACE_CONTAINER_HIGHEST if is_empty else ft.Colors.SURFACE_CONTAINER_HIGH
                    text_color = ft.Colors.GREY_500 if is_empty else ft.Colors.ON_SURFACE

                    card = ft.Container(
                        content=ft.Row([
                            ft.Container(content=ft.Text(pair['time'], weight=ft.FontWeight.BOLD, color=text_color, no_wrap=True), width=110),
                            ft.Column([
                                ft.Text(pair['subject'], size=16, weight=ft.FontWeight.BOLD, color=text_color),
                                ft.Text(f"{pair['teacher']}" if pair['teacher'] else "", size=14, color=text_color),
                            ], expand=True),
                            ft.Container(content=ft.Text(pair['room'] if pair['room'] else "", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200), width=50, alignment=ft.Alignment.CENTER_RIGHT)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=15, border_radius=ft.BorderRadius.all(12), bgcolor=bg_color,
                        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT) if not is_empty else None
                    )
                    schedule_list.controls.append(card)
            page.update()

        def change_date(delta):
            nonlocal current_view_date
            current_view_date += timedelta(days=delta)
            status_text.value = "Добро пожаловать!"
            show_schedule_for_date(current_view_date)

        def go_to_date(target_date):
            nonlocal current_view_date
            current_view_date = target_date
            status_text.value = "Добро пожаловать!"
            show_schedule_for_date(current_view_date)

        def open_settings(e):
            def save_settings(e):
                config["theme"] = "dark" if theme_switch.value else "light"
                config["cleanup_enabled"] = cleanup_switch.value
                cfg.save_config(config)
                page.theme_mode = ft.ThemeMode.DARK if theme_switch.value else ft.ThemeMode.LIGHT
                settings_dialog.open = False
                page.update()

            def change_group_click(e):
                settings_dialog.open = False
                page.update()
                show_startup_screen()

            theme_switch = ft.Switch(label="Темная тема", value=config.get("theme") == "dark")
            cleanup_switch = ft.Switch(label="Чистка >30 файлов", value=config.get("cleanup_enabled", True))

            settings_dialog = ft.AlertDialog(
                title=ft.Text("Настройки"),
                content=ft.Column([
                    ft.Text(f"Группа: {config['group']}", weight=ft.FontWeight.BOLD),
                    ft.TextButton("Сменить группу", on_click=change_group_click),
                    ft.Divider(),
                    theme_switch,
                    cleanup_switch,
                ], tight=True, spacing=20),
                actions=[ft.TextButton("Сохранить", on_click=save_settings)],
                modal=True
            )
            if settings_dialog not in page.overlay:
                page.overlay.append(settings_dialog)
            settings_dialog.open = True
            page.update()

        header_date = ft.Text(current_view_date.strftime("%d.%m.%Y"), size=28, weight=ft.FontWeight.BOLD)
        status_text = ft.Text("Добро пожаловать!", color=ft.Colors.GREY_400, size=12)
        schedule_list = ft.ListView(spacing=10, expand=True, padding=0)
        
        btn_open_disk = ft.IconButton(ft.Icons.OPEN_IN_NEW, icon_size=28, on_click=lambda _: webbrowser.open(YANDEX_URL))
        btn_settings = ft.IconButton(ft.Icons.SETTINGS, icon_size=28, on_click=open_settings)
        btn_refresh = ft.IconButton(ft.Icons.REFRESH, icon_size=28, on_click=refresh_data)
        
        top_bar = ft.Row([
            ft.Text(f"Группа {config['group']}", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
            ft.Row([btn_open_disk, btn_refresh, btn_settings], spacing=0)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        date_control_row = ft.Row([
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda _: change_date(-1)),
            header_date, 
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda _: change_date(1)),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
        
        today_date = date.today()
        btn_yesterday = ft.Button(content=ft.Text("Вчера", no_wrap=True), width=110, height=40, on_click=lambda _: go_to_date(today_date - timedelta(days=1)))
        btn_today = ft.Button(content=ft.Text("Сегодня", no_wrap=True), width=110, height=40, on_click=lambda _: go_to_date(today_date))
        btn_tomorrow = ft.Button(content=ft.Text("Завтра", no_wrap=True), width=110, height=40, on_click=lambda _: go_to_date(today_date + timedelta(days=1)))

        date_buttons_row = ft.Row(
            [btn_yesterday, btn_today, btn_tomorrow],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )

        main_content = ft.Column([
            top_bar,
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            date_control_row, 
            ft.Row([date_buttons_row], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([status_text], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(height=10, color=ft.Colors.OUTLINE_VARIANT),
            schedule_list 
        ], expand=True)
        
        page.add(main_content)
        show_schedule_for_date(current_view_date)

    show_startup_loading()

if __name__ == "__main__":
    import traceback
    try: 
        ft.run(main)
    except Exception as e:
        
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(f"❌ ПРОИЗОШЛА ОШИБКА ПРИ ЗАПУСКЕ:\n")
            f.write(traceback.format_exc())
        
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"Произошла ошибка. Подробности в файле error_log.txt\n\n{e}", "Ошибка Schedule Tracker", 0x10)
