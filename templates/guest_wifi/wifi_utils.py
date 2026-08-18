import pandas as pd
import io
from datetime import datetime
from templates.base.database_helper import db
from flask import send_file
from models import GuestWifi
from logger import logger

def export_guest_wifi_to_excel():
    """Экспорт данных гостевого WiFi в Excel"""
    logger.info('Экспорт гостевого WiFi в Excel')
    wifi_data = GuestWifi.query.order_by(GuestWifi.city, GuestWifi.organization).all()
    
    rows = []
    for wifi in wifi_data:
        rows.append({
            'Город': wifi.city,
            'Стоимость': float(wifi.price) if wifi.price is not None else 0,
            'Организация': wifi.organization,
            'Статус': wifi.status,
            'SSID': wifi.ssid,
            'Пароль': wifi.password,
            'IP диапазон': wifi.ip_range,
            'Скорость': wifi.speed,
            'Номер договора': wifi.contract_number,
            'Дата договора': wifi.contract_date,
            'Контактное лицо': wifi.contact_person,
            'Телефон': wifi.phone,
            'Email': wifi.email,
            'Дата установки': wifi.installation_date,
            'Дата продления': wifi.renewal_date,
            'Примечания': wifi.notes,
            'Дата создания': wifi.created_at,
            'Дата обновления': wifi.updated_at
        })
    
    # Преобразуем в DataFrame
    columns = [
        'Город', 'Стоимость', 'Организация', 'Статус', 'SSID',
        'Пароль', 'IP диапазон', 'Скорость', 'Номер договора',
        'Дата договора', 'Контактное лицо', 'Телефон', 'Email',
        'Дата установки', 'Дата продления', 'Примечания',
        'Дата создания', 'Дата обновления'
    ]
    
    df = pd.DataFrame(rows, columns=columns)
    
    # Форматируем числовые колонки
    if 'Стоимость' in df.columns:
        df['Стоимость'] = pd.to_numeric(df['Стоимость'], errors='coerce')
    
    stats_rows = [
        {
            'city': wifi.city,
            'price': float(wifi.price) if wifi.price is not None else 0,
            'organization': wifi.organization,
            'status': wifi.status,
            'ssid': wifi.ssid,
            'password': wifi.password,
            'ip_range': wifi.ip_range,
            'speed': wifi.speed,
            'contract_number': wifi.contract_number,
            'contract_date': wifi.contract_date,
            'contact_person': wifi.contact_person,
            'phone': wifi.phone,
            'email': wifi.email,
            'installation_date': wifi.installation_date,
            'renewal_date': wifi.renewal_date,
            'notes': wifi.notes,
            'created_at': wifi.created_at,
            'updated_at': wifi.updated_at
        }
        for wifi in wifi_data
    ]

    # Создаем Excel файл в памяти
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Основной лист с данными
        df.to_excel(writer, sheet_name='Гостевой WiFi', index=False)
        
        # Лист со статистикой
        stats_data = generate_wifi_stats(stats_rows)
        stats_df = pd.DataFrame([stats_data])
        stats_df.to_excel(writer, sheet_name='Статистика', index=False)
        
        # Настраиваем ширину колонок
        worksheet = writer.sheets['Гостевой WiFi']
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 50)
    
    output.seek(0)
    return output

def generate_wifi_stats(wifi_data):
    """Генерирует статистику по гостевому WiFi"""
    if not wifi_data:
        return {
            'Всего точек': 0,
            'Активных точек': 0,
            'Неактивных точек': 0,
            'Общая стоимость (руб/мес)': 0,
            'Городов': 0,
            'Организаций': 0
        }
    
    df = pd.DataFrame(wifi_data, columns=[
        'city', 'price', 'organization', 'status', 'ssid', 
        'password', 'ip_range', 'speed', 'contract_number',
        'contract_date', 'contact_person', 'phone', 'email',
        'installation_date', 'renewal_date', 'notes',
        'created_at', 'updated_at'
    ])
    
    # Преобразуем цену в числовой формат
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    stats = {
        'Всего точек': len(df),
        'Активных точек': len(df[df['status'] == 'Активен']),
        'Неактивных точек': len(df[df['status'] == 'Неактивен']),
        'Общая стоимость (руб/мес)': df['price'].sum(),
        'Городов': df['city'].nunique(),
        'Организаций': df['organization'].nunique()
    }
    
    return stats

def import_guest_wifi_from_excel(file):
    """Импорт данных гостевого WiFi из Excel файла"""
    try:
        logger.info('Импорт гостевого WiFi из Excel')
        df = pd.read_excel(file)
        
        column_mapping = {
            'Город': 'city',
            'Стоимость': 'price', 
            'Организация': 'organization',
            'Статус': 'status',
            'SSID': 'ssid',
            'Пароль': 'password',
            'IP диапазон': 'ip_range',
            'Скорость': 'speed',
            'Номер договора': 'contract_number',
            'Дата договора': 'contract_date',
            'Контактное лицо': 'contact_person',
            'Телефон': 'phone',
            'Email': 'email',
            'Дата установки': 'installation_date',
            'Дата продления': 'renewal_date',
            'Примечания': 'notes'
        }
        
        df = df.rename(columns=column_mapping)
        available_columns = [col for col in column_mapping.values() if col in df.columns]
        df = df[available_columns]
        
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                row_data = {}
                for col in available_columns:
                    value = row[col]
                    if pd.isna(value):
                        value = None
                    elif col == 'price' and value is not None:
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            value = 0.0
                    elif col in ['contract_number', 'phone'] and value is not None:
                        if isinstance(value, float) and not pd.isna(value):
                            value = str(int(value))
                        else:
                            value = str(value)
                    elif isinstance(value, pd.Timestamp):
                        value = value.strftime('%Y-%m-%d')
                    row_data[col] = value
                
                if not row_data.get('city'):
                    errors.append(f"Строка {index + 2}: Отсутствует город")
                    continue
                
                wifi_record = GuestWifi(**row_data)
                db.session.add(wifi_record)
                imported_count += 1
            except Exception as e:
                logger.error(f'Ошибка при обработке строки {index + 2} импорта гостевого WiFi: {e}', exc_info=True)
                errors.append(f"Строка {index + 2}: {str(e)}")
                continue
        
        db.session.commit()
        
        if errors:
            return False, f"Успешно импортировано {imported_count} записей. Ошибки: {'; '.join(errors)}"
        return True, f"Успешно импортировано {imported_count} записей"
    except Exception as e:
        db.session.rollback()
        logger.error(f'Ошибка при импорте гостевого WiFi из Excel: {e}', exc_info=True)
        return False, f"Ошибка при импорте файла: {str(e)}"

def create_wifi_template():
    """Создает шаблон Excel файла для импорта гостевого WiFi"""
    logger.info('Генерация шаблона Excel для импорта гостевого WiFi')
    
    # Создаем DataFrame с примером данных
    sample_data = {
        'Город': ['Москва', 'Санкт-Петербург'],
        'Стоимость': [1500.00, 1200.50],
        'Организация': ['ООО "Телеком"', 'ИП Иванов'],
        'Статус': ['Активен', 'Активен'],
        'SSID': ['Guest_Moscow', 'Guest_SPB'],
        'Пароль': ['password123', 'securepass'],
        'IP диапазон': ['192.168.1.0/24', '10.0.0.0/24'],
        'Скорость': ['100 Мбит/с', '50 Мбит/с'],
        'Номер договора': ['ДГ-2024-001', 'ДГ-2024-002'],
        'Дата договора': ['2024-01-15', '2024-01-20'],
        'Контактное лицо': ['Иванов Иван', 'Петров Петр'],
        'Телефон': ['+79991234567', '+79997654321'],
        'Email': ['ivanov@mail.com', 'petrov@mail.com'],
        'Дата установки': ['2024-01-20', '2024-01-25'],
        'Дата продления': ['2025-01-20', '2025-01-25'],
        'Примечания': ['Основная точка', 'Резервная точка']
    }
    
    df = pd.DataFrame(sample_data)
    
    # Создаем Excel файл в памяти
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Лист с примером данных
        df.to_excel(writer, sheet_name='Пример данных', index=False)
        
        # Лист с инструкцией
        instructions = [
            ['ИНСТРУКЦИЯ ПО ЗАПОЛНЕНИЮ'],
            [''],
            ['Обязательные поля:'],
            ['- Город (обязательно)'],
            [''],
            ['Необязательные поля:'],
            ['- Все остальные поля можно оставить пустыми'],
            [''],
            ['Форматы данных:'],
            ['- Дата: ГГГГ-ММ-ДД (например: 2024-01-15)'],
            ['- Стоимость: число с десятичными знаками (например: 1500.50)'],
            ['- Статус: Активен, Неактивен, В процессе'],
            [''],
            ['ВАЖНО:'],
            ['- Удалите примеры данных перед загрузкой своих данных'],
            ['- Сохраняйте формат колонок'],
            ['- Не изменяйте названия колонок']
        ]
        
        instructions_df = pd.DataFrame(instructions)
        instructions_df.to_excel(writer, sheet_name='Инструкция', index=False, header=False)
        
        # Настраиваем ширину колонок для листа с примером
        worksheet = writer.sheets['Пример данных']
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 30)
    
    output.seek(0)
    return output

def download_wifi_template():
    """Скачивание шаблона для импорта гостевого WiFi"""
    logger.info('Скачивание шаблона гостевого WiFi')
    template_file = create_wifi_template()
    
    return send_file(
        template_file,
        download_name=f'guest_wifi_template_{datetime.now().strftime("%Y%m%d")}.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
