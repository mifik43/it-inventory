import pandas as pd
import io
from datetime import datetime
from templates.base.database import get_db

def get_supported_exel_types_mapping():
    table_mapping = {
                'devices.devices': 'devices',
                'providers.providers': 'providers', 
                'cubes.cubes': 'software_cubes',
                'organizations.organizations': 'organizations',
                'todos.todos': 'todos'
            }
    
    return table_mapping

def generate_export_filename(data_type):
    
    table_mapping = get_supported_exel_types_mapping()
    
    if data_type not in table_mapping:
        raise Exception('Неподдерживаемый тип данных для экспорта')
    
    table_name = table_mapping[data_type]
    filename = f'{table_name}_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
    return filename

def export_to_excel(table_name, columns=None):
    """Экспорт данных из таблицы в Excel"""
    db = get_db()
    
    # Определяем какие столбцы экспортировать
    if columns is None:
        # Получаем все столбцы таблицы
        table_info = db.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = [col['name'] for col in table_info if col['name'] not in ['id', 'created_at', 'updated_at']]
    
    # Получаем данные
    columns_str = ', '.join(columns)
    data = db.execute(f"SELECT {columns_str} FROM {table_name}").fetchall()
    
    # Преобразуем в DataFrame
    df = pd.DataFrame(data, columns=columns)
    
    # Создаем Excel файл в памяти
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=table_name, index=False)
    
    output.seek(0)
    return output

def import_from_excel(file, data_type, column_mapping=None):
    """Импорт данных из Excel в таблицу"""
    db = get_db()

    # проверка на поддерживаемый тип
    table_mapping = get_supported_exel_types_mapping()
    if data_type not in table_mapping:
        raise Exception('Неподдерживаемый тип данных для импорта')
    
    table_name = table_mapping[data_type]

    try:
        # Читаем Excel файл
        df = pd.read_excel(file)
        
        # Преобразуем названия столбцов если нужно
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # Получаем информацию о таблице
        table_info = db.execute(f"PRAGMA table_info({table_name})").fetchall()
        table_columns = [col['name'] for col in table_info if col['name'] not in ['id', 'created_at', 'updated_at']]
        
        # Оставляем только нужные столбцы
        df = df[[col for col in table_columns if col in df.columns]]
        
        # Импортируем данные
        for _, row in df.iterrows():
            # Заменяем NaN на None
            row_data = {k: (v if pd.notna(v) else None) for k, v in row.items()}
            
            # Создаем SQL запрос
            columns = ', '.join(row_data.keys())
            placeholders = ', '.join(['?' for _ in row_data])
            
            db.execute(
                f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
                list(row_data.values())
            )
        
        db.commit()
        return True, f"Успешно импортировано {len(df)} записей"
        
    except Exception as e:
        db.rollback()
        return False, f"Ошибка импорта: {str(e)}"

def export_devices():
    """Экспорт устройств в Excel"""
    return export_to_excel('devices', [
        'name', 'model', 'type', 'serial_number', 'mac_address', 
        'ip_address', 'location', 'status', 'assigned_to', 'specifications'
    ])

def export_providers():
    """Экспорт провайдеров в Excel"""
    return export_to_excel('providers', [
        'name', 'service_type', 'contract_number', 'contract_date', 
        'ip_range', 'speed', 'price', 'contact_person', 'phone', 
        'email', 'object_location', 'city', 'status', 'notes'
    ])

def export_cubes():
    """Экспорт программных кубов в Excel"""
    return export_to_excel('software_cubes', [
        'name', 'software_type', 'license_type', 'license_key', 
        'contract_number', 'contract_date', 'price', 'users_count',
        'support_contact', 'phone', 'email', 'object_location', 
        'city', 'status', 'renewal_date', 'notes'
    ])

def export_organizations():
    """Экспорт организаций в Excel"""
    return export_to_excel('organizations', [
        'name', 'type', 'inn', 'contact_person', 'phone', 
        'email', 'address', 'notes'
    ])

def export_todos():
    """Экспорт задач в Excel"""
    return export_to_excel('todos', [
        'title', 'description', 'status', 'priority', 
        'organization_id', 'due_date', 'is_completed'
    ])

def export_wtware():
    """Экспорт конфигураций WTware в Excel"""
    return export_to_excel('wtware_configs', [
        'name', 'version', 'server_ip', 'server_port', 'screen_width', 
        'screen_height', 'auto_start', 'network_drive', 'printer_config',
        'startup_script', 'shutdown_script', 'status', 'notes'
    ])


def export_any_type_to_exel(data_type):

    if data_type == 'devices.devices':
        return export_devices()
    elif data_type == 'providers.providers':
        return export_providers()
    elif data_type == 'cubes.cubes':
        return export_cubes()
    elif data_type == 'organizations.organizations':
        return export_organizations()
    elif data_type == 'todos.todos':
        return export_todos()
    else:
        raise Exception('Неподдерживаемый тип данных для экспорта')