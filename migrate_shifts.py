from database import get_db
from datetime import datetime, timedelta

def migrate_shifts():
    db = get_db()
    try:
        # Создаем таблицу смен
        db.execute('''
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                shift_date DATE NOT NULL,
                shift_type TEXT NOT NULL,
                start_time TIME,
                end_time TIME,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Добавляем тестовые данные
        users = db.execute('SELECT id FROM users').fetchall()
        if users:
            user_ids = [user['id'] for user in users]
            
            shift_types = ['Утро', 'День', 'Вечер', 'Ночь']
            test_shifts = []
            
            today = datetime.now().date()
            
            for i in range(7):  # На 7 дней вперед
                shift_date = today + timedelta(days=i)
                for user_id in user_ids:
                    shift_type = shift_types[i % len(shift_types)]
                    start_time = f"{8 + (i % 3)}:00"
                    end_time = f"{17 + (i % 3)}:00"
                    
                    test_shifts.append((
                        user_id,
                        shift_date.strftime('%Y-%m-%d'),
                        shift_type,
                        start_time,
                        end_time,
                        f'Тестовая смена {i+1}'
                    ))
            
            for shift in test_shifts:
                db.execute('''
                    INSERT INTO shifts (user_id, shift_date, shift_type, start_time, end_time, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', shift)
        
        db.commit()
        print("✅ Таблица смен успешно создана и заполнена тестовыми данными!")
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблицы смен: {e}")

if __name__ == '__main__':
    migrate_shifts()