import sqlite3
from werkzeug.security import generate_password_hash

def get_db():
    conn = sqlite3.connect('it_inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    
    # Таблица устройств
    db.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            model TEXT,
            type TEXT NOT NULL,
            serial_number TEXT UNIQUE,
            mac_address TEXT,
            ip_address TEXT,
            location TEXT NOT NULL,
            status TEXT NOT NULL,
            assigned_to TEXT,
            specifications TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица пользователей
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица провайдеров
    db.execute('''
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            service_type TEXT NOT NULL,
            contract_number TEXT,
            contract_date DATE,
            ip_range TEXT,
            speed TEXT,
            price DECIMAL(10,2),
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            object_location TEXT NOT NULL,
            city TEXT NOT NULL DEFAULT 'Не указан',
            status TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица кубиков (программное обеспечение)
    db.execute('''
        CREATE TABLE IF NOT EXISTS software_cubes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            software_type TEXT NOT NULL,
            license_type TEXT NOT NULL,
            license_key TEXT,
            contract_number TEXT,
            contract_date DATE,
            price DECIMAL(10,2),
            users_count INTEGER,
            support_contact TEXT,
            phone TEXT,
            email TEXT,
            object_location TEXT NOT NULL,
            city TEXT NOT NULL DEFAULT 'Не указан',
            status TEXT NOT NULL,
            renewal_date DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица логов
    db.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            user TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Таблица организаций
    db.execute('''
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'ООО',
            inn TEXT,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Таблица задач
    db.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'новая',
            priority TEXT DEFAULT 'средний',
            organization_id INTEGER,
            due_date DATE,
            completed_at TIMESTAMP,
            is_completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations (id)
        )
    ''')
    # Таблица статей
    db.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Общее',
            tags TEXT,
            author_id INTEGER NOT NULL,
            is_published BOOLEAN DEFAULT 1,
            views INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES users (id)
        )
    ''')

    # Таблица заметок
    db.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            color TEXT DEFAULT '#ffffff',
            is_pinned BOOLEAN DEFAULT 0,
            author_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES users (id)
        )
    ''')
    # Добавляем администратора по умолчанию
    cursor = db.execute('SELECT COUNT(*) as count FROM users')
    count = cursor.fetchone()['count']
    
    if count == 0:
        admin_password = generate_password_hash('admin123')
        db.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            ('admin', admin_password, 'admin')
        )
        
        # Добавляем тестового пользователя
        user_password = generate_password_hash('user123')
        db.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            ('user', user_password, 'user')
        )
    
        
    
    db.commit()