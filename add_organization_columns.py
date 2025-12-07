import sqlite3

def migrate_database():
    conn = sqlite3.connect('your_database1.db')
    cursor = conn.cursor()
    
    # Список таблиц для обновления
    tables = [
        ('devices', 'organization_id'),
        ('providers', 'organization_id'),
        ('guest_wifi', 'organization_id'),
        ('cubes', 'organization_id'),
        ('wtware_configs', 'organization_id'),
        ('shifts', 'organization_id'),
        ('notes', 'organization_id'),
        ('articles', 'organization_id'),
        ('todos', 'organization_id'),
    ]
    
    for table, column in tables:
        try:
            # Проверяем, существует ли колонка
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            if column not in columns:
                print(f"Adding {column} to {table}...")
                cursor.execute(f'''
                    ALTER TABLE {table} 
                    ADD COLUMN {column} INTEGER REFERENCES organizations(id)
                ''')
            else:
                print(f"Column {column} already exists in {table}")
                
        except Exception as e:
            print(f"Error updating {table}: {e}")
    
    # Создаем индексы для ускорения запросов
    indexes = [
        ('devices', 'organization_id'),
        ('providers', 'organization_id'),
        ('guest_wifi', 'organization_id'),
        ('cubes', 'organization_id'),
        ('wtware_configs', 'organization_id'),
        ('shifts', 'organization_id'),
        ('notes', 'organization_id'),
        ('articles', 'organization_id'),
        ('todos', 'organization_id'),
    ]
    
    for table, column in indexes:
        try:
            index_name = f"idx_{table}_{column}"
            cursor.execute(f'''
                CREATE INDEX IF NOT EXISTS {index_name} 
                ON {table}({column})
            ''')
            print(f"Created index {index_name}")
        except Exception as e:
            print(f"Error creating index for {table}.{column}: {e}")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == '__main__':
    migrate_database()