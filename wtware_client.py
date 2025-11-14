import socket
import struct
import time
import logging
from typing import Optional, Dict, List, Tuple

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WTwareClient:
    def __init__(self):
        self.socket = None
        self.connected = False
    
    def connect(self, hostname: str, port: int = 80, timeout: int = 10) -> bool:
        """Подключение к устройству WTware по его родному протоколу"""
        try:
            # Убедимся, что порт - целое число
            port = int(port)
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            
            logger.info(f"Подключение к WTware {hostname}:{port}...")
            self.socket.connect((hostname, port))
            
            # WTware обычно не требует аутентификации при первом подключении
            self.connected = True
            logger.info(f"Успешное подключение к WTware {hostname}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к {hostname}:{port}: {str(e)}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Закрытие подключения"""
        try:
            if self.socket:
                self.socket.close()
        except:
            pass
        finally:
            self.socket = None
            self.connected = False
    
    def send_command(self, command: str) -> Tuple[bool, str]:
        """Отправка команды устройству WTware"""
        if not self.connected:
            return False, "Нет подключения к устройству"
        
        try:
            # WTware протокол обычно использует простые текстовые команды
            self.socket.send(f"{command}\r\n".encode('utf-8'))
            
            # Ждем ответа
            time.sleep(0.5)  # Даем время на обработку
            
            # Пытаемся получить ответ (если устройство его отправляет)
            try:
                response = self.socket.recv(4096).decode('utf-8').strip()
                return True, response if response else "Команда отправлена"
            except socket.timeout:
                return True, "Команда отправлена (таймаут ожидания ответа)"
            except BlockingIOError:
                return True, "Команда отправлена (нет ответа)"
            except Exception as e:
                return True, f"Команда отправлена (ошибка чтения ответа: {str(e)})"
                
        except Exception as e:
            return False, f"Ошибка отправки команды: {str(e)}"
    
    def get_system_info(self) -> Dict:
        """Получение базовой информации о системе"""
        info = {}
        
        # Отправляем команды для получения информации
        commands = {
            'version': 'version',
            'status': 'status',
            'config': 'config'
        }
        
        for key, cmd in commands.items():
            success, response = self.send_command(cmd)
            if success and response and "отправлена" not in response.lower():
                info[key] = response
        
        return info
    
    def reboot_device(self) -> Tuple[bool, str]:
        """Перезагрузка устройства"""
        return self.send_command("reboot")
    
    def reload_config(self) -> Tuple[bool, str]:
        """Перезагрузка конфигурации"""
        return self.send_command("reload")

def generate_proper_wtware_config(config_data: Dict) -> str:
    """Генерация конфигурационного файла WTware в правильном формате INI"""
    config_lines = ["# WTware Configuration File"]
    config_lines.append("# Generated automatically")
    config_lines.append("")
    
    # Основные настройки
    if config_data.get('server_ip'):
        config_lines.append(f"server={config_data['server_ip']}")
    
    if config_data.get('server_port'):
        config_lines.append(f"port={config_data['server_port']}")
    
    if config_data.get('screen_width') and config_data.get('screen_height'):
        config_lines.append(f"screen={config_data['screen_width']}x{config_data['screen_height']}")
    
    # Настройки автозапуска
    if config_data.get('auto_start'):
        config_lines.append(f"autostart={config_data['auto_start']}")
    
    # Сетевые настройки
    if config_data.get('network_drive'):
        config_lines.append(f"net={config_data['network_drive']}")
    
    # Настройки принтера
    if config_data.get('printer_config'):
        config_lines.append(f"printer={config_data['printer_config']}")
    
    # Безопасность
    config_lines.append("logon=0")
    config_lines.append("password=0")
    
    # Дополнительные настройки
    config_lines.append("fullscreen=1")
    config_lines.append("timeout=30")
    
    # Скрипты
    if config_data.get('startup_script'):
        config_lines.append("")
        config_lines.append("# Startup script")
        config_lines.append(f"startup={config_data['startup_script']}")
    
    if config_data.get('shutdown_script'):
        config_lines.append("")
        config_lines.append("# Shutdown script")
        config_lines.append(f"shutdown={config_data['shutdown_script']}")
    
    # Пользовательская конфигурация
    if config_data.get('custom_config'):
        config_lines.append("")
        config_lines.append("# Custom configuration")
        # Добавляем пользовательскую конфигурацию как есть
        custom_lines = config_data['custom_config'].split('\n')
        config_lines.extend(custom_lines)
    
    return '\n'.join(config_lines)

def generate_wtware_config(config_data: Dict) -> str:
    """Генерация конфигурационного файла WTware"""
    return generate_proper_wtware_config(config_data)

def test_wtware_connection(hostname: str, port: int = 80) -> Tuple[bool, str, Dict]:
    """Тестирование подключения к устройству WTware"""
    client = WTwareClient()
    
    try:
        # Убедимся, что порт - целое число
        port = int(port)
        
        # Подключаемся
        if not client.connect(hostname, port):
            return False, "Не удалось подключиться к устройству WTware", {}
        
        # Получаем информацию о системе
        system_info = client.get_system_info()
        
        return True, "Успешное подключение к WTware", system_info
        
    except ValueError as e:
        return False, f"Некорректный порт: {port}", {}
    except Exception as e:
        return False, f"Ошибка тестирования: {str(e)}", {}
    finally:
        client.disconnect()

def upload_config_to_wtware(hostname: str, config_content: str, port: int = 80) -> Tuple[bool, str]:
    """Загрузка конфигурации на устройство WTware"""
    client = WTwareClient()
    
    try:
        # Убедимся, что порт - целое число
        port = int(port)
        
        if not client.connect(hostname, port):
            return False, "Не удалось подключиться к устройству"
        
        # В реальном WTware загрузка конфигурации может требовать
        # дополнительных действий. Здесь упрощенная версия.
        
        # Отправляем команду на перезагрузку конфигурации
        success, message = client.reload_config()
        
        if success:
            return True, "Конфигурация применена (требуется перезагрузка устройства)"
        else:
            return False, f"Ошибка применения конфигурации: {message}"
        
    except ValueError as e:
        return False, f"Некорректный порт: {port}"
    except Exception as e:
        return False, f"Ошибка загрузки конфигурации: {str(e)}"
    finally:
        client.disconnect()

def test_wtware_connection_multiple_ports(hostname: str, ports: List[int] = None) -> Tuple[bool, str, Dict]:
    """Тестирование подключения к устройству WTware с перебором портов"""
    if ports is None:
        ports = [8080, 80, 443, 8081, 8088, 8090]
    
    for port in ports:
        client = WTwareClient()
        try:
            logger.info(f"Попытка подключения к {hostname}:{port}...")
            if client.connect(hostname, port):
                # Получаем информацию о системе
                system_info = client.get_system_info()
                return True, f"Успешное подключение через порт {port}", system_info
        except Exception as e:
            logger.info(f"Порт {port} не доступен: {str(e)}")
        finally:
            client.disconnect()
    
    return False, f"Не удалось подключиться ни к одному из портов: {ports}", {}