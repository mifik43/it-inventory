from datetime import datetime
from templates.base.database_helper import db
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, DECIMAL, Date, Time, Numeric
from sqlalchemy.orm import relationship

class User(db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default='user')
    email = Column(String(100))
    full_name = Column(String(200))
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    shifts = relationship('Shift', backref='user', lazy=True)
    articles = relationship('Article', backref='author', lazy=True)
    notes = relationship('Note', backref='author', lazy=True)
    social_posts = relationship('SocialPost', backref='user', lazy=True)
    social_platforms = relationship('SocialPlatform', backref='user', lazy=True)
    scheduled_posts = relationship('ScheduledPost', backref='user', lazy=True)
    
    def get_id(self):
        return str(self.id)

class Device(db.Model):
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    model = Column(String(100))
    type = Column(String(50), nullable=False)
    serial_number = Column(String(100), unique=True)
    mac_address = Column(String(50))
    ip_address = Column(String(50))
    location = Column(String(200), nullable=False)
    status = Column(String(50), nullable=False, default='active')
    assigned_to = Column(String(200))
    specifications = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Provider(db.Model):
    __tablename__ = 'providers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    service_type = Column(String(100), nullable=False)
    contract_number = Column(String(100))
    contract_date = Column(Date)
    ip_range = Column(String(100))
    speed = Column(String(50))
    price = Column(DECIMAL(10, 2))
    contact_person = Column(String(200))
    phone = Column(String(20))
    email = Column(String(100))
    object_location = Column(String(200), nullable=False)
    city = Column(String(100), default='Не указан')
    status = Column(String(50), nullable=False, default='Активен')
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class SoftwareCube(db.Model):
    __tablename__ = 'software_cubes'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    software_type = Column(String(100), nullable=False)
    license_type = Column(String(100), nullable=False)
    license_key = Column(String(200))
    contract_number = Column(String(100))
    contract_date = Column(Date)
    price = Column(DECIMAL(10, 2))
    users_count = Column(Integer)
    support_contact = Column(String(200))
    phone = Column(String(20))
    email = Column(String(100))
    object_location = Column(String(200), nullable=False)
    city = Column(String(100), default='Не указан')
    status = Column(String(50), nullable=False, default='Активен')
    renewal_date = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Organization(db.Model):
    __tablename__ = 'organizations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50), default='ООО')
    inn = Column(String(20))
    contact_person = Column(String(200))
    phone = Column(String(20))
    email = Column(String(100))
    address = Column(String(300))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    todos = relationship('Todo', backref='organization', lazy=True)

class Todo(db.Model):
    __tablename__ = 'todos'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='новая')
    priority = Column(String(50), default='средний')
    organization_id = Column(Integer, ForeignKey('organizations.id'))
    due_date = Column(Date)
    completed_at = Column(DateTime)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Shift(db.Model):
    __tablename__ = 'shifts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    shift_date = Column(Date, nullable=False)
    shift_type = Column(String(50), nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Article(db.Model):
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), default='Общее')
    tags = Column(String(300))
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_published = Column(Boolean, default=True)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    screenshots = relationship('ArticleScreenshot', backref='article', lazy=True)
    social_posts = relationship('SocialPost', backref='article', lazy=True)

class Note(db.Model):
    __tablename__ = 'notes'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    color = Column(String(20), default='#ffffff')
    is_pinned = Column(Boolean, default=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    social_posts = relationship('SocialPost', backref='note', lazy=True)

class ArticleScreenshot(db.Model):
    __tablename__ = 'article_screenshots'
    
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False)
    filename = Column(String(200), nullable=False)
    original_filename = Column(String(200), nullable=False)
    file_size = Column(Integer)
    description = Column(Text)
    upload_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class GuestWifi(db.Model):
    __tablename__ = 'guest_wifi'
    
    id = Column(Integer, primary_key=True)
    city = Column(String(100), nullable=False)
    price = Column(DECIMAL(10, 2))
    organization = Column(String(200))
    status = Column(String(50), default='Активен')
    ssid = Column(String(100))
    password = Column(String(100))
    ip_range = Column(String(100))
    speed = Column(String(50))
    contract_number = Column(String(100))
    contract_date = Column(String(50))
    contact_person = Column(String(200))
    phone = Column(String(20))
    email = Column(String(100))
    installation_date = Column(String(50))
    renewal_date = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WtwareConfig(db.Model):
    __tablename__ = 'wtware_configs'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    version = Column(String(50))
    server_ip = Column(String(50))
    server_port = Column(Integer, default=80)
    screen_width = Column(Integer, default=1024)
    screen_height = Column(Integer, default=768)
    auto_start = Column(String(100))
    network_drive = Column(String(200))
    printer_config = Column(Text)
    startup_script = Column(Text)
    shutdown_script = Column(Text)
    custom_config = Column(Text)
    status = Column(String(50), default='Активна')
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deployments = relationship('WtwareDeployment', backref='config', lazy=True)

class WtwareDeployment(db.Model):
    __tablename__ = 'wtware_deployments'
    
    id = Column(Integer, primary_key=True)
    config_id = Column(Integer, ForeignKey('wtware_configs.id'), nullable=False)
    device_ip = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    error_message = Column(Text)
    deployed_at = Column(DateTime, default=datetime.utcnow)

class Script(db.Model):
    __tablename__ = 'scripts'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    filename = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    results = relationship('ScriptResult', backref='script', lazy=True)

class ScriptResult(db.Model):
    __tablename__ = 'script_results'
    
    id = Column(Integer, primary_key=True)
    script_id = Column(Integer, ForeignKey('scripts.id'))
    executed_at = Column(DateTime, default=datetime.utcnow)
    output = Column(Text)
    success = Column(Boolean)
    error_message = Column(Text)
    execution_time = Column(Float)

class NetworkScan(db.Model):
    __tablename__ = 'network_scans'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    scan_type = Column(String(50), nullable=False)
    target_range = Column(String(200), nullable=False)
    status = Column(String(50), default='running')
    devices_found = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    notes = Column(Text)
    devices = relationship('NetworkDevice', backref='scan', lazy=True)

class NetworkDevice(db.Model):
    __tablename__ = 'network_devices'
    
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey('network_scans.id'))
    ip_address = Column(String(50), nullable=False)
    mac_address = Column(String(50))
    hostname = Column(String(200))
    vendor = Column(String(200))
    os_info = Column(String(200))
    ports = Column(Text)
    status = Column(String(50), default='online')
    response_time = Column(Float)
    last_seen = Column(DateTime, default=datetime.utcnow)

class SocialPost(db.Model):
    __tablename__ = 'social_posts'
    
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('articles.id'))
    note_id = Column(Integer, ForeignKey('notes.id'))
    content = Column(Text, nullable=False)
    platforms = Column(String(200), nullable=False)
    media_files = Column(Text)
    results = Column(Text)
    published_at = Column(DateTime, default=datetime.utcnow)
    scheduled_time = Column(DateTime)
    status = Column(String(50), default='draft')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SocialPlatform(db.Model):
    __tablename__ = 'social_platforms'
    
    id = Column(Integer, primary_key=True)
    platform_name = Column(String(100), nullable=False)
    platform_type = Column(String(50), nullable=False)
    api_key = Column(Text)
    api_secret = Column(Text)
    access_token = Column(Text)
    token_secret = Column(Text)
    group_id = Column(String(100))
    channel_id = Column(String(100))
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ScheduledPost(db.Model):
    __tablename__ = 'scheduled_posts'
    
    id = Column(Integer, primary_key=True)
    source_type = Column(String(50), nullable=False)
    source_id = Column(Integer, nullable=False)
    platforms = Column(String(200), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(String(50), default='scheduled')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    permissions = relationship('Permission', secondary='role_permissions', backref='roles')

class Permission(db.Model):
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class RolePermission(db.Model):
    __tablename__ = 'role_permissions'
    
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    permission_id = Column(Integer, ForeignKey('permissions.id'), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserRole(db.Model):
    __tablename__ = 'roles_to_user'
    
    role_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Log(db.Model):
    __tablename__ = 'logs'
    
    id = Column(Integer, primary_key=True)
    action = Column(String(200), nullable=False)
    user = Column(String(200), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ChecklistTask(db.Model):
    __tablename__ = 'checklist_tasks'
    
    id = Column(Integer, primary_key=True)
    task_number = Column(String(50))
    stage = Column(String(100), nullable=False)
    task_description = Column(Text, nullable=False)
    category = Column(String(100))
    comment = Column(Text)
    status = Column(String(50), default='Не начато')
    planned_date = Column(Date)
    actual_date = Column(Date)
    responsible = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChecklistHistory(db.Model):
    __tablename__ = 'checklist_history'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('checklist_tasks.id'))
    changed_field = Column(String(50))
    old_value = Column(Text)
    new_value = Column(Text)
    changed_by = Column(String(100))
    changed_at = Column(DateTime, default=datetime.utcnow)