import pandas as pd
import io
from datetime import datetime
from database import get_db


def export_guest_wifi_to_excel():
    """Экспорт данных гостевого WiFi в Excel"""
    db = get_db()
    
    # Получаем данные гостевого WiFi
    wifi_data = db.execute('''
        SELECT 
            city, price, organization, status, ssid, 
            password, ip_range, speed, contract_number,
            contract_date, contact_person, phone, email,
            installation_date, renewal_date, notes,
            created_at, updated_at
        FROM guest_wifi 
        ORDER BY city, organization
    ''').fetchall()
    
    # Преобразуем в DataFrame
    columns = [
        'Город', 'Стоимость', 'Организация', 'Статус', 'SSID',
        'Пароль', 'IP диапазон', 'Скорость', 'Номер договора',
        'Дата договора', 'Контактное лицо', 'Телефон', 'Email',
        'Дата установки', 'Дата продления', 'Примечания',
        'Дата создания', 'Дата обновления'
    ]
    
    df = pd.DataFrame(wifi_data, columns=columns)
    
    # Форматируем числовые колонки
    if 'Стоимость' in df.columns:
        df['Стоимость'] = pd.to_numeric(df['Стоимость'], errors='coerce')
    
    # Создаем Excel файл в памяти
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Основной лист с данными
        df.to_excel(writer, sheet_name='Гостевой WiFi', index=False)
        
        # Лист со статистикой
        stats_data = generate_wifi_stats(wifi_data)
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
    db = get_db()
    
    try:
        # Читаем Excel файл
        df = pd.read_excel(file)
        
        # Сопоставляем названия колонок (русские -> английские)
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
        
        # Переименовываем колонки
        df = df.rename(columns=column_mapping)
        
        # Оставляем только нужные колонки
        available_columns = [col for col in column_mapping.values() if col in df.columns]
        df = df[available_columns]
        
        # Обрабатываем данные перед вставкой
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Подготавливаем данные
                row_data = {}
                for col in available_columns:
                    value = row[col]
                    
                    # Обрабатываем специальные случаи
                    if pd.isna(value):
                        value = None
                    elif col == 'price' and value is not None:
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            value = 0.0
                    elif isinstance(value, (int, float)) and pd.notna(value):
                        # Для числовых полей, которые должны быть строками
                        if col in ['contract_number', 'phone']:
                            value = str(int(value)) if not pd.isna(value) else None
                    
                    row_data[col] = value
                
                # Проверяем обязательные поля
                if not row_data.get('city'):
                    errors.append(f"Строка {index + 2}: Отсутствует город")
                    continue
                
                # Вставляем данные
                columns = ', '.join(row_data.keys())
                placeholders = ', '.join(['?' for _ in row_data])
                
                db.execute(
                    f"INSERT INTO guest_wifi ({columns}) VALUES ({placeholders})",
                    list(row_data.values())
                )
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Строка {index + 2}: {str(e)}")
                continue
        
        db.commit()
        
        if errors:
            return False, f"Успешно импортировано {imported_count} записей. Ошибки: {'; '.join(errors)}"
        else:
            return True, f"Успешно импортировано {imported_count} записей"
        
    except Exception as e:
        db.rollback()
        return False, f"Ошибка при импорте файла: {str(e)}"

def create_wifi_template():
    """Создает шаблон Excel файла для импорта гостевого WiFi"""
    
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
    template_file = create_wifi_template()
    
    return send_file(
        template_file,
        download_name=f'guest_wifi_template_{datetime.now().strftime("%Y%m%d")}.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
