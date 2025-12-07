import sqlite3

def migrate_database():
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()
    
    # Список таблиц для обновления
    tables = [
        'todos',
        'devices', 
        'providers',
        'guest_wifi',
        'cubes',
        'wtware_configs',
        'shifts',
        'notes',
        'articles'
    ]
    
    for table in tables:
        try:
            # Проверяем, существует ли колонка organization_id
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'organization_id' not in columns:
                print(f"Adding organization_id to {table}...")
                cursor.execute(f'''
                    ALTER TABLE {table} 
                    ADD COLUMN organization_id INTEGER REFERENCES organizations(id)
                ''')
                
                # Создаем индекс для ускорения запросов
                cursor.execute(f'''
                    CREATE INDEX IF NOT EXISTS idx_{table}_organization 
                    ON {table}(organization_id)
                ''')
        except Exception as e:
            print(f"Error updating {table}: {e}")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == '__main__':
    migrate_database()