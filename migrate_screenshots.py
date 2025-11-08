from database import get_db

def migrate_screenshots():
    db = get_db()
    try:
        # Создаем таблицу для скриншотов
        db.execute('''
            CREATE TABLE IF NOT EXISTS article_screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_size INTEGER,
                description TEXT,
                upload_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles (id) ON DELETE CASCADE
            )
        ''')
        
        db.commit()
        print("✅ Таблица для скриншотов успешно создана!")
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблицы скриншотов: {e}")

if __name__ == '__main__':
    migrate_screenshots()