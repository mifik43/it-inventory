from database import get_db

def migrate_organizations():
    db = get_db()
    try:
        # Добавляем новые столбцы в таблицу organizations
        db.execute('ALTER TABLE organizations ADD COLUMN type TEXT DEFAULT "ООО"')
        db.execute('ALTER TABLE organizations ADD COLUMN inn TEXT')
        db.execute('ALTER TABLE organizations ADD COLUMN contact_person TEXT')
        db.execute('ALTER TABLE organizations ADD COLUMN phone TEXT')
        db.execute('ALTER TABLE organizations ADD COLUMN email TEXT')
        db.execute('ALTER TABLE organizations ADD COLUMN address TEXT')
        db.execute('ALTER TABLE organizations ADD COLUMN notes TEXT')
        
        # Обновляем существующие записи
        db.execute('UPDATE organizations SET type = "ООО" WHERE type IS NULL')
        
        db.commit()
        print("✅ База данных успешно обновлена! Добавлены новые поля для организаций")
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении базы данных: {e}")

if __name__ == '__main__':
    migrate_organizations()