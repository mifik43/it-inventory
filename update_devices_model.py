from database import get_db

def update_database():
    db = get_db()
    try:
        # Добавляем столбец model в таблицу devices
        db.execute('ALTER TABLE devices ADD COLUMN model TEXT')
        db.commit()
        print("✅ База данных успешно обновлена! Добавлен столбец 'model'")
        
        # Обновляем существующие записи (если есть)
        cursor = db.execute("SELECT COUNT(*) as count FROM devices")
        count = cursor.fetchone()['count']
        print(f"✅ Найдено устройств: {count}")
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении базы данных: {e}")

if __name__ == '__main__':
    update_database()