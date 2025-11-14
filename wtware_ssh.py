import paramiko
import io
import logging
from typing import Optional, Dict, List, Tuple

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WTwareSSHClient:
    def __init__(self):
        self.ssh_client = None
        self.sftp_client = None
    
    def connect(self, hostname: str, username: str, password: str, port: int = 22) -> bool:
        """Подключение к устройству WTware по SSH"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            logger.info(f"Подключение к {hostname}:{port}...")
            self.ssh_client.connect(
                hostname=hostname,
                username=username,
                password=password,
                port=port,
                timeout=10
            )
            
            # Создаем SFTP клиент для передачи файлов
            self.sftp_client = self.ssh_client.open_sftp()
            logger.info(f"Успешное подключение к {hostname}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к {hostname}: {str(e)}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Закрытие подключения"""
        try:
            if self.sftp_client:
                self.sftp_client.close()
            if self.ssh_client:
                self.ssh_client.close()
        except:
            pass
        finally:
            self.ssh_client = None
            self.sftp_client = None
    
    def execute_command(self, command: str) -> Tuple[bool, str]:
        """Выполнение команды на устройстве"""
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            
            if error:
                return False, error
            return True, output
            
        except Exception as e:
            return False, str(e)
    
    def upload_config(self, local_config_content: str, remote_path: str = "/etc/wtware.conf") -> Tuple[bool, str]:
        """Загрузка конфигурационного файла на устройство"""
        try:
            # Создаем временный файл в памяти
            config_file = io.BytesIO(local_config_content.encode('utf-8'))
            
            # Загружаем файл на устройство
            self.sftp_client.putfo(config_file, remote_path)
            
            # Перезагружаем службу WTware
            success, message = self.execute_command("systemctl restart wtware")
            if not success:
                return False, f"Файл загружен, но не удалось перезапустить службу: {message}"
            
            return True, "Конфигурация успешно загружена и применена"
            
        except Exception as e:
            return False, f"Ошибка загрузки конфигурации: {str(e)}"
    
    def download_config(self, remote_path: str = "/etc/wtware.conf") -> Tuple[bool, str]:
        """Скачивание текущей конфигурации с устройства"""
        try:
            # Создаем временный файл в памяти
            config_file = io.BytesIO()
            
            # Скачиваем файл с устройства
            self.sftp_client.getfo(remote_path, config_file)
            
            # Получаем содержимое
            config_content = config_file.getvalue().decode('utf-8')
            return True, config_content
            
        except Exception as e:
            return False, f"Ошибка скачивания конфигурации: {str(e)}"
    
    def get_system_info(self) -> Dict:
        """Получение информации о системе"""
        info = {}
        
        # Получаем версию WTware
        success, output = self.execute_command("wtware --version")
        if success:
            info['wtware_version'] = output
        
        # Получаем информацию о системе
        success, output = self.execute_command("uname -a")
        if success:
            info['system_info'] = output
        
        # Получаем информацию о сети
        success, output = self.execute_command("ip addr show")
        if success:
            info['network_info'] = output
        
        # Получаем список процессов
        success, output = self.execute_command("ps aux")
        if success:
            info['processes'] = output
        
        return info
    
    def reboot_device(self) -> Tuple[bool, str]:
        """Перезагрузка устройства"""
        return self.execute_command("reboot")
    
    def restart_wtware(self) -> Tuple[bool, str]:
        """Перезапуск службы WTware"""
        return self.execute_command("systemctl restart wtware")

def generate_wtware_config(config_data: Dict) -> str:
    """Генерация конфигурационного файла WTware"""
    config_lines = []
    
    # Основные настройки
    if config_data.get('server_ip'):
        config_lines.append(f"server {config_data['server_ip']}")
    
    if config_data.get('server_port'):
        config_lines.append(f"port {config_data['server_port']}")
    
    if config_data.get('screen_width') and config_data.get('screen_height'):
        config_lines.append(f"screen {config_data['screen_width']}x{config_data['screen_height']}")
    
    if config_data.get('auto_start'):
        config_lines.append(f"autostart {config_data['auto_start']}")
    
    if config_data.get('network_drive'):
        config_lines.append(f"net {config_data['network_drive']}")
    
    if config_data.get('printer_config'):
        config_lines.append(f"printer {config_data['printer_config']}")
    
    # Скрипты
    if config_data.get('startup_script'):
        config_lines.append("\n# Startup script")
        config_lines.append(f"startup {config_data['startup_script']}")
    
    if config_data.get('shutdown_script'):
        config_lines.append("\n# Shutdown script")
        config_lines.append(f"shutdown {config_data['shutdown_script']}")
    
    # Пользовательская конфигурация
    if config_data.get('custom_config'):
        config_lines.append("\n# Custom configuration")
        config_lines.append(config_data['custom_config'])
    
    return '\n'.join(config_lines)

def test_wtware_connection(hostname: str, username: str, password: str, port: int = 22) -> Tuple[bool, str, Dict]:
    """Тестирование подключения к устройству WTware"""
    client = WTwareSSHClient()
    
    try:
        # Подключаемся
        if not client.connect(hostname, username, password, port):
            return False, "Не удалось подключиться к устройству", {}
        
        # Получаем информацию о системе
        system_info = client.get_system_info()
        
        # Проверяем наличие WTware
        if 'wtware_version' not in system_info:
            return False, "WTware не обнаружен на устройстве", system_info
        
        return True, "Успешное подключение", system_info
        
    except Exception as e:
        return False, f"Ошибка тестирования: {str(e)}", {}
    finally:
        client.disconnect()