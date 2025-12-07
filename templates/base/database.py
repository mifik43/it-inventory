import sqlite3
from werkzeug.security import generate_password_hash
from flask import g

from templates.roles.database_roles import create_roles_tables, find_role_by_name, save_roles_to_user_by_id
from templates.base.database_helper import get_db

def find_user_id_by_name(user_name:str, db:sqlite3.Connection = get_db()):
    user = db.execute(f"SELECT id FROM users where username=\"{user_name}\"").fetchone()
    if user is None:
        raise ValueError(f"Пользователь {user_name} не найден")
    
    return user["id"]

def set_role_for_user(user_name, role_name, db:sqlite3.Connection):
    role = find_role_by_name(role_name, db)
    if role is None:
        raise ValueError(f"Роль {role_name} не найдена")
    
    user_id = find_user_id_by_name(user_name, db)
    save_roles_to_user_by_id(user_id, [role["id"]], db, False)


def init_default_admin(db:sqlite3.Connection):

    # Добавляем администратора по умолчанию
    cursor = db.execute('SELECT COUNT(*) as count FROM users')
    count = cursor.fetchone()['count']
    
    if count == 0:
        print("Админ по умолчанию не найден. Создаём")
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

        super_admin_role = find_role_by_name("SuperAdmin", db)
        if super_admin_role is None:
            raise ValueError("Роль SuperAdmin не найдена")
        

        set_role_for_user("admin", "SuperAdmin", db)
        set_role_for_user("user", "Reader", db)
        
DATABASE = 'database.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

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
    # Таблица смен
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
    # Таблица для скриншотов статей
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

    # Таблица по гостевому WIFI
    db.execute('''
        CREATE TABLE IF NOT EXISTS guest_wifi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            price DECIMAL(10,2),
            organization TEXT,
            status TEXT DEFAULT 'Активен',
            ssid TEXT,
            password TEXT,
            ip_range TEXT,
            speed TEXT,
            contract_number TEXT,
            contract_date TEXT,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            installation_date TEXT,
            renewal_date TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
    ''')
    # Таблица wtware
    db.execute('''
        CREATE TABLE IF NOT EXISTS wtware_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            version TEXT,
            server_ip TEXT,
            server_port INTEGER DEFAULT 80,
            screen_width INTEGER DEFAULT 1024,
            screen_height INTEGER DEFAULT 768,
            auto_start TEXT,
            network_drive TEXT,
            printer_config TEXT,
            startup_script TEXT,
            shutdown_script TEXT,
            custom_config TEXT,
            status TEXT DEFAULT 'Активна',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS wtware_deployments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_id INTEGER NOT NULL,
            device_ip TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (config_id) REFERENCES wtware_configs (id)
        );        ''')
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            filename TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица для хранения результатов выполнения скриптов
    db.execute('''
        CREATE TABLE IF NOT EXISTS script_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            script_id INTEGER,
            executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            output TEXT,
            success BOOLEAN,
            error_message TEXT,
            execution_time REAL,
            FOREIGN KEY (script_id) REFERENCES scripts (id)
        )
    ''')

    # Таблица для хранения сессий сканирования
    db.execute('''
        CREATE TABLE IF NOT EXISTS network_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            scan_type TEXT NOT NULL,
            target_range TEXT NOT NULL,
            status TEXT DEFAULT 'running',
            devices_found INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            notes TEXT
        )
    ''')
    
    # Таблица для хранения обнаруженных устройств
    db.execute('''
        CREATE TABLE IF NOT EXISTS network_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            ip_address TEXT NOT NULL,
            mac_address TEXT,
            hostname TEXT,
            vendor TEXT,
            os_info TEXT,
            ports TEXT,
            status TEXT DEFAULT 'online',
            response_time REAL,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scan_id) REFERENCES network_scans (id)
        )
    ''')

    db.execute('''
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
            status TEXT DEFAULT 'draft', -- draft, scheduled, published, failed
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles (id),
            FOREIGN KEY (note_id) REFERENCES notes (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    db.execute('''
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
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL, -- article, note
            source_id INTEGER NOT NULL,
            platforms TEXT NOT NULL,
            scheduled_time TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'scheduled', -- scheduled, processing, completed, failed
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    db.execute('''
            CREATE TABLE IF NOT EXISTS user_organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                organization_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
                UNIQUE(user_id, organization_id)
            )
        ''')
     # После создания таблиц проверяем и добавляем недостающие колонки
    add_organization_columns(db)
    db.commit()

def add_organization_columns(db):
    """Добавляет колонку organization_id в таблицы, если она отсутствует"""
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
    
    for table in tables:
        try:
            # Проверяем, существует ли колонка organization_id
            db.execute(f"SELECT organization_id FROM {table} LIMIT 1")
        except sqlite3.OperationalError:
            # Колонки нет, добавляем
            db.execute(f'''
                ALTER TABLE {table} 
                ADD COLUMN organization_id INTEGER REFERENCES organizations(id)
            ''')
            print(f"Added organization_id column to {table}")
            
            # Создаем индекс
            db.execute(f'''
                CREATE INDEX IF NOT EXISTS idx_{table}_organization 
                ON {table}(organization_id)
            ''')
    
    # Проверяем и создаем таблицу user_organizations, если ее нет
    try:
        db.execute("SELECT 1 FROM user_organizations LIMIT 1")
    except sqlite3.OperationalError:
        db.execute('''
            CREATE TABLE IF NOT EXISTS user_organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                organization_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
                UNIQUE(user_id, organization_id)
            )
        ''')
    
    db.execute('CREATE INDEX IF NOT EXISTS idx_user_organizations_user ON user_organizations(user_id)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_user_organizations_org ON user_organizations(organization_id)')
    
    # Добавляем администратора по умолчанию
    create_roles_tables(db)
    init_default_admin(db)
    
    db.commit()

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()