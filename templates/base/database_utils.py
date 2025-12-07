import sqlite3


def check_table_structure(table_name):
    """Проверяет структуру таблицы и возвращает список колонок"""
    db = get_db()
    
    try:
        result = db.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = []
        for row in result:
            columns.append({
                'name': row[1],
                'type': row[2],
                'notnull': row[3],
                'default': row[4],
                'pk': row[5]
            })
        return columns
    except Exception as e:
        return []

def has_column(table_name, column_name):
    """Проверяет, существует ли колонка в таблице"""
    columns = check_table_structure(table_name)
    return any(col['name'] == column_name for col in columns)

def get_missing_columns():
    """Возвращает список таблиц, в которых нет колонки organization_id"""
    tables = [
        'devices',
        'providers', 
        'guest_wifi',
        'cubes',
        'wtware_configs',
        'shifts',
        'notes',
        'articles',
        'todos'
    ]
    
    missing = []
    for table in tables:
        if not has_column(table, 'organization_id'):
            missing.append(table)
    
    return missing