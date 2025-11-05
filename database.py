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
    
    # Добавляем тестовые устройства, если таблица пустая
    cursor = db.execute('SELECT COUNT(*) as count FROM devices')
    count = cursor.fetchone()['count']
    
    if count == 0:
        sample_devices = [
            ('Ноутбук Dell XPS 13', 'XPS 13 9310', 'Ноутбук', 'SN-DELL-001', '00:1B:44:11:3A:B7', '192.168.1.100', 'Офис 101', 'В использовании', 'Иванов Иван', 'Intel i7, 16GB RAM, 512GB SSD'),
            ('Монитор Samsung', 'S24F350', 'Монитор', 'SN-SAMS-001', '', '', 'Офис 101', 'В использовании', 'Иванов Иван', '24 дюйма, 1920x1080'),
            ('Сервер HP ProLiant', 'DL380 Gen10', 'Сервер', 'SN-HP-001', '00:1B:44:11:3A:B8', '192.168.1.10', 'Серверная', 'В использовании', '', 'Xeon E5, 32GB RAM, 1TB HDD'),
        ]
        
        db.executemany('''
            INSERT INTO devices 
            (name, model, type, serial_number, mac_address, ip_address, location, status, assigned_to, specifications)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_devices)
    
    # Добавляем тестовых провайдеров
    cursor = db.execute('SELECT COUNT(*) as count FROM providers')
    count = cursor.fetchone()['count']
    
    if count == 0:
        sample_providers = [
            ('Ростелеком', 'Интернет', 'ДГ-2023-001', '2023-01-15', '192.168.1.0/24', '100 Мбит/с', 5000.00, 'Петров А.С.', '+7-999-123-45-67', 'petrov@rostelecom.ru', 'Офис на Ленина 25', 'Москва', 'Активен', 'Основной провайдер'),
            ('МТС', 'Интернет + Телефония', 'ДГ-2023-002', '2023-02-20', '192.168.2.0/24', '50 Мбит/с', 3500.00, 'Сидорова М.В.', '+7-999-765-43-21', 'sidorova@mts.ru', 'Складской комплекс', 'Санкт-Петербург', 'Активен', 'Резервный канал'),
        ]
        
        db.executemany('''
            INSERT INTO providers 
            (name, service_type, contract_number, contract_date, ip_range, speed, price, contact_person, phone, email, object_location, city, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_providers)
    
    # Добавляем тестовые кубики
    cursor = db.execute('SELECT COUNT(*) as count FROM software_cubes')
    count = cursor.fetchone()['count']
    
    if count == 0:
        sample_cubes = [
            ('Microsoft 365', 'Офисный пакет', 'Корпоративная', 'MS-365-KEY-001', 'ЛЦ-2023-001', '2023-01-10', 15000.00, 25, 'Смирнов А.В.', '+7-999-111-22-33', 'smirnov@microsoft.com', 'Головной офис', 'Москва', 'Активен', '2024-01-10', 'Лицензия на 25 пользователей'),
            ('1C:Бухгалтерия', 'Бухгалтерская система', 'Профессиональная', '1C-BUH-KEY-001', 'ЛЦ-2023-002', '2023-02-15', 50000.00, 1, 'Кузнецова М.И.', '+7-999-444-55-66', 'kuznetsova@1c.ru', 'Бухгалтерия', 'Москва', 'Активен', '2024-02-15', 'Основная бухгалтерская система'),
            ('Kaspersky Endpoint Security', 'Антивирус', 'Корпоративная', 'KES-KEY-001', 'ЛЦ-2023-003', '2023-03-20', 30000.00, 50, 'Орлов Д.С.', '+7-999-777-88-99', 'orlov@kaspersky.ru', 'Все рабочие станции', 'Москва', 'Активен', '2024-03-20', 'Защита всех рабочих станций'),
            ('Confluence', 'Корпоративный портал', 'Enterprise', 'CONF-KEY-001', 'ЛЦ-2023-004', '2023-04-05', 120000.00, 100, 'Техподдержка Atlassian', '+7-800-555-35-35', 'support@atlassian.com', 'Все филиалы', 'Москва', 'Активен', '2024-04-05', 'Корпоративная вики и документация'),
        ]
        
        db.executemany('''
            INSERT INTO software_cubes 
            (name, software_type, license_type, license_key, contract_number, contract_date, price, users_count, support_contact, phone, email, object_location, city, status, renewal_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_cubes)
    
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