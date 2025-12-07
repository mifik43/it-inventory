import sqlite3

def migrate_database():
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()
    
    # Добавляем новые разрешения в таблицу ролей (если нужно)
    # В вашем случае разрешения хранятся как строки, так что новая роль
    # будет содержать их автоматически при создании через интерфейс
    
    # Создаем таблицы для социальных сетей если их нет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS social_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            note_id INTEGER,
            content TEXT NOT NULL,
            platforms TEXT NOT NULL,
            media_files TEXT,
            results TEXT,
            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            scheduled_time TIMESTAMP,
            status TEXT DEFAULT 'draft',
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles (id),
            FOREIGN KEY (note_id) REFERENCES notes (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS social_platforms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform_name TEXT NOT NULL,
            platform_type TEXT NOT NULL,
            api_key TEXT,
            api_secret TEXT,
            access_token TEXT,
            token_secret TEXT,
            group_id TEXT,
            channel_id TEXT,
            is_active INTEGER DEFAULT 1,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            platforms TEXT NOT NULL,
            scheduled_time TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'scheduled',
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Миграция базы данных завершена")

if __name__ == '__main__':
    migrate_database()