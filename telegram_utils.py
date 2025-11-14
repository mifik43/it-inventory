import requests
import json
from datetime import datetime
from database import get_db
from flask import current_app

class TelegramBot:
    def __init__(self, token=None, webhook_url=None):
        self.token = token
        self.webhook_url = webhook_url
        self.base_url = f"https://api.telegram.org/bot{token}/"

    def set_webhook(self):
        """Установка webhook для бота"""
        if not self.token or not self.webhook_url:
            return False, "Токен или URL webhook не установлен"
        
        url = f"{self.base_url}setWebhook"
        data = {
            "url": self.webhook_url,
            "drop_pending_updates": True
        }
        
        try:
            response = requests.post(url, json=data)
            result = response.json()
            return result.get('ok', False), result.get('description', 'Unknown error')
        except Exception as e:
            return False, str(e)

    def send_message(self, chat_id, text, parse_mode='HTML', reply_markup=None):
        """Отправка сообщения пользователю"""
        if not self.token:
            return False, "Токен бота не установлен"
        
        url = f"{self.base_url}sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            data['reply_markup'] = reply_markup
        
        try:
            response = requests.post(url, json=data)
            result = response.json()
            return result.get('ok', False), result
        except Exception as e:
            return False, str(e)

    def create_inline_keyboard(self, buttons):
        """Создание inline клавиатуры"""
        return {
            "inline_keyboard": buttons
        }

def save_telegram_request(telegram_data):
    """Сохранение заявки из Telegram в базу данных"""
    db = get_db()
    
    try:
        message = telegram_data.get('message', {})
        chat = message.get('chat', {})
        
        # Извлекаем данные из сообщения
        telegram_id = chat.get('id')
        username = chat.get('username')
        first_name = chat.get('first_name')
        last_name = chat.get('last_name')
        message_text = message.get('text', '')
        
        # Определяем категорию по ключевым словам
        category = categorize_message(message_text)
        
        # Сохраняем заявку
        cursor = db.execute('''
            INSERT INTO telegram_requests 
            (telegram_id, username, first_name, last_name, message_text, category)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (telegram_id, username, first_name, last_name, message_text, category))
        
        request_id = cursor.lastrowid
        db.commit()
        
        return True, request_id
        
    except Exception as e:
        return False, str(e)

def categorize_message(text):
    """Автоматическая категоризация сообщения по ключевым словам"""
    text_lower = text.lower()
    
    categories = {
        'wifi': ['wifi', 'вайфай', 'интернет', 'сеть', 'подключить', 'пароль'],
        'hardware': ['компьютер', 'ноутбук', 'принтер', 'монитор', 'клавиатура', 'мышь', 'ремонт'],
        'software': ['программа', 'софт', 'установить', 'лицензия', 'windows', 'office'],
        'access': ['доступ', 'логин', 'пароль', 'учетка', 'аккаунт'],
        'phone': ['телефон', 'звонок', 'связь', 'мобильный'],
        'other': []
    }
    
    for category, keywords in categories.items():
        if any(keyword in text_lower for keyword in keywords):
            return category
    
    return 'other'

def get_telegram_requests(status=None, limit=50):
    """Получение заявок из Telegram"""
    db = get_db()
    
    query = '''
        SELECT tr.*, 
               u1.username as assigned_username,
               u2.username as response_username
        FROM telegram_requests tr
        LEFT JOIN users u1 ON tr.assigned_to = u1.id
        LEFT JOIN users u2 ON tr.response_by = u2.id
    '''
    
    params = []
    if status:
        query += ' WHERE tr.status = ?'
        params.append(status)
    
    query += ' ORDER BY tr.created_at DESC LIMIT ?'
    params.append(limit)
    
    return db.execute(query, params).fetchall()

def update_request_status(request_id, status, user_id=None):
    """Обновление статуса заявки"""
    db = get_db()
    
    try:
        db.execute('''
            UPDATE telegram_requests 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, request_id))
        
        db.commit()
        return True
    except Exception as e:
        return False

def assign_request(request_id, user_id):
    """Назначение заявки на пользователя"""
    db = get_db()
    
    try:
        db.execute('''
            UPDATE telegram_requests 
            SET assigned_to = ?, status = 'assigned', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id, request_id))
        
        db.commit()
        return True
    except Exception as e:
        return False

def add_response(request_id, response_text, user_id):
    """Добавление ответа к заявке"""
    db = get_db()
    
    try:
        db.execute('''
            UPDATE telegram_requests 
            SET response_text = ?, response_by = ?, response_at = CURRENT_TIMESTAMP,
                status = 'completed', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (response_text, user_id, request_id))
        
        db.commit()
        return True
    except Exception as e:
        return False

def get_request_stats():
    """Статистика по заявкам"""
    db = get_db()
    
    stats = db.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) as new_count,
            SUM(CASE WHEN status = 'assigned' THEN 1 ELSE 0 END) as assigned_count,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
            COUNT(DISTINCT telegram_id) as unique_users
        FROM telegram_requests
    ''').fetchone()
    
    return dict(stats) if stats else {}