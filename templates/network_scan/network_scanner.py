import subprocess
import ipaddress
import platform
import socket
import threading
import time
from datetime import datetime
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for

from templates.base.database import get_db
from templates.base.requirements import permission_required, permissions_required_all, permissions_required_any
from templates.roles.permissions import Permissions


bluprint_network_scan_routes = Blueprint("network_scan", __name__)

# ========== МАРШРУТЫ ДЛЯ СКАНИРОВАНИЯ СЕТИ ==========
@bluprint_network_scan_routes.route('/network_scan')
@permission_required(Permissions.guest_wifi_manage)
def network_scan():
    """Главная страница сканирования сети"""
    db = get_db()
    
    # Получаем последние сканирования
    scans = db.execute('''
        SELECT * FROM network_scans 
        ORDER BY created_at DESC 
        LIMIT 10
    ''').fetchall()
    
    return render_template('network_scan/network_scan.html', scans=scans)

@bluprint_network_scan_routes.route('/network_scan/start', methods=['POST'])

def start_network_scan():
    """Запуск сканирования сети"""
    scan_type = request.form['scan_type']
    target_range = request.form['target_range']
    scan_name = request.form.get('scan_name', f'Scan {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    
    # Валидация target_range
    if scan_type == 'ping':
        if not target_range:
            flash('Для ping-сканирования необходимо указать сетевой диапазон', 'error')
            return redirect(url_for('network_scan'))
        
        if not validate_network_range(target_range):
            flash('Неверный формат сетевого диапазона. Примеры: 192.168.1.0/24, 192.168.1.1-100, 192.168.1.1', 'error')
            return redirect(url_for('network_scan'))
    
    elif scan_type == 'arp':
        # Для ARP-сканирования target_range не обязателен
        if not target_range:
            target_range = 'auto'  # Автоматическое определение локальной сети
    
    db = get_db()
    
    try:
        # Создаем запись о сканировании
        scan_id = db.execute('''
            INSERT INTO network_scans (name, scan_type, target_range, status)
            VALUES (?, ?, ?, ?)
        ''', (scan_name, scan_type, target_range, 'running')).lastrowid
        db.commit()
        
        # Запускаем сканирование в отдельном потоке
        import threading
        scan_thread = threading.Thread(
            target=run_network_scan_background,
            args=(scan_id, scan_type, target_range)
        )
        scan_thread.daemon = True
        scan_thread.start()
        
        flash('Сканирование сети запущено!', 'success')
        
    except Exception as e:
        flash(f'Ошибка при запуске сканирования: {str(e)}', 'error')
    
    return redirect(url_for('network_scan.network_scan'))

def run_network_scan_background(scan_id, scan_type, target_range):
    """Фоновая задача сканирования сети"""
    with app.app_context():
        db = get_db()
        try:
            # Запускаем сканирование
            devices = network_scanner.start_scan(scan_type, target_range)
            
            # Сохраняем найденные устройства
            for device in devices:
                db.execute('''
                    INSERT INTO network_devices 
                    (scan_id, ip_address, mac_address, hostname, vendor, os_info, ports, response_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    scan_id,
                    device['ip_address'],
                    device.get('mac_address', 'Unknown'),
                    device.get('hostname', 'Unknown'),
                    device.get('vendor', 'Unknown'),
                    device.get('os_info', 'Unknown'),
                    json.dumps(device.get('ports', [])),
                    device.get('response_time', 0)
                ))
            
            # Обновляем статус сканирования
            db.execute('''
                UPDATE network_scans 
                SET status = 'completed', 
                    devices_found = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (len(devices), scan_id))
            db.commit()
            
        except Exception as e:
            # В случае ошибки обновляем статус
            db.execute('''
                UPDATE network_scans 
                SET status = 'failed',
                    notes = ?
                WHERE id = ?
            ''', (str(e), scan_id))
            db.commit()

@bluprint_network_scan_routes.route('/network_scan/<int:scan_id>')

def network_scan_results(scan_id):
    """Результаты сканирования"""
    db = get_db()
    
    scan = db.execute('SELECT * FROM network_scans WHERE id = ?', (scan_id,)).fetchone()
    devices = db.execute('''
        SELECT * FROM network_devices 
        WHERE scan_id = ? 
        ORDER BY ip_address
    ''', (scan_id,)).fetchall()
    
    # Парсим JSON для портов
    processed_devices = []
    for device in devices:
        device_dict = dict(device)
        if device_dict['ports']:
            try:
                device_dict['ports'] = json.loads(device_dict['ports'])
            except:
                device_dict['ports'] = []
        processed_devices.append(device_dict)
    
    return render_template('network_scan/scan_results.html', 
                         scan=scan, 
                         devices=processed_devices)

@bluprint_network_scan_routes.route('/network_scan/progress')

def network_scan_progress():
    """Получение прогресса сканирования"""
    return jsonify({
        'is_scanning': network_scanner.is_scanning,
        'progress': network_scanner.scan_progress
    })

@bluprint_network_scan_routes.route('/network_scan/stop', methods=['POST'])

def stop_network_scan():
    """Остановка сканирования"""
    network_scanner.is_scanning = False
    flash('Сканирование остановлено', 'info')
    return redirect(url_for('network_scan'))

@bluprint_network_scan_routes.route('/network_devices')

def network_devices():
    """Список всех обнаруженных устройств"""
    db = get_db()
    
    devices = db.execute('''
        SELECT nd.*, ns.name as scan_name, ns.created_at as scan_date
        FROM network_devices nd
        JOIN network_scans ns ON nd.scan_id = ns.id
        ORDER BY nd.last_seen DESC
    ''').fetchall()
    
    # Обрабатываем порты
    processed_devices = []
    for device in devices:
        device_dict = dict(device)
        if device_dict['ports']:
            try:
                device_dict['ports'] = json.loads(device_dict['ports'])
            except:
                device_dict['ports'] = []
        processed_devices.append(device_dict)
    
    # Получаем статистику для шаблона
    vendors = set()
    for device in devices:
        if device['vendor'] != 'Unknown':
            vendors.add(device['vendor'])
    
    # Получаем количество сканирований
    scans_count = db.execute('SELECT COUNT(*) as count FROM network_scans').fetchone()['count']
    
    # Получаем дату последнего сканирования
    last_scan = db.execute('SELECT created_at FROM network_scans ORDER BY created_at DESC LIMIT 1').fetchone()
    last_scan_date = last_scan['created_at'][:10] if last_scan else 'Нет данных'
    
    return render_template('network_scan/devices_list.html', 
                         devices=processed_devices,
                         vendors_count=len(vendors),
                         scans_count=scans_count,
                         last_scan_date=last_scan_date)

@bluprint_network_scan_routes.route('/network_scan/delete/<int:scan_id>')

def delete_network_scan(scan_id):
    """Удаление сканирования"""
    db = get_db()
    
    try:
        # Удаляем устройства сканирования
        db.execute('DELETE FROM network_devices WHERE scan_id = ?', (scan_id,))
        # Удаляем само сканирование
        db.execute('DELETE FROM network_scans WHERE id = ?', (scan_id,))
        db.commit()
        flash('Сканирование и все связанные устройства удалены!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении: {str(e)}', 'error')
    
    return redirect(url_for('network_scan.network_scan'))

@bluprint_network_scan_routes.route('/network_scan/ping/<ip>')

def ping_device(ip):
    """Пинг устройства"""
    try:
        import platform
        param = "-n 1 -w 2000" if platform.system().lower() == "windows" else "-c 1 -W 2"
        command = f"ping {param} {ip}"
        
        start_time = time.time()
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            shell=True,
            timeout=5
        )
        end_time = time.time()
        
        success = result.returncode == 0
        response_time = round((end_time - start_time) * 1000, 2) if success else 0
        
        return jsonify({
            'success': success,
            'ip': ip,
            'response_time': response_time,
            'output': result.stdout,
            'error': result.stderr if not success else ''
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Timeout', 'ip': ip})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'ip': ip})

@bluprint_network_scan_routes.route('/network_scan/device_info/<int:device_id>')

def device_info(device_id):
    """Информация об устройстве"""
    db = get_db()
    device = db.execute('''
        SELECT nd.*, ns.name as scan_name 
        FROM network_devices nd
        JOIN network_scans ns ON nd.scan_id = ns.id
        WHERE nd.id = ?
    ''', (device_id,)).fetchone()
    
    if device:
        device_dict = dict(device)
        if device_dict['ports']:
            try:
                device_dict['ports'] = json.loads(device_dict['ports'])
            except:
                device_dict['ports'] = []
        return jsonify({'success': True, 'device': device_dict})
    else:
        return jsonify({'success': False, 'error': 'Устройство не найдено'})

@bluprint_network_scan_routes.route('/network_scan/delete_device/<int:device_id>', methods=['POST'])

def delete_device(device_id):
    """Удаление устройства"""
    db = get_db()
    try:
        db.execute('DELETE FROM network_devices WHERE id = ?', (device_id,))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def validate_network_range(network_range):
    """Валидация сетевого диапазона"""
    try:
        # Проверка CIDR формата
        if '/' in network_range:
            ipaddress.ip_network(network_range, strict=False)
            return True
        
        # Проверка диапазона IP
        if '-' in network_range:
            base_ip, end = network_range.split('-')
            ipaddress.ip_address(base_ip)  # Проверяем базовый IP
            end_ip = int(end)
            if 1 <= end_ip <= 255:
                return True
            return False
        
        # Проверка одиночного IP
        ipaddress.ip_address(network_range)
        return True
        
    except:
        return False

# Вспомогательная функция для шаблонов
@bluprint_network_scan_routes.context_processor
def utility_processor():
    def get_port_service(port):
        port_services = {
            21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
            80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS', 993: 'IMAPS',
            995: 'POP3S', 1433: 'MSSQL', 1521: 'Oracle', 3306: 'MySQL',
            3389: 'RDP', 5432: 'PostgreSQL', 5900: 'VNC', 8080: 'HTTP-Alt'
        }
        return port_services.get(port, 'Unknown')
    return dict(get_port_service=get_port_service)

# Улучшенный NetworkScanner с исправлениями
class NetworkScanner:
    def __init__(self):
        self.active_devices = []
        self.scan_progress = 0
        self.is_scanning = False
        
    def ping_sweep(self, network_range, timeout=2):
        """
        Улучшенное ping сканирование сети
        """
        devices = []
        
        try:
            # Парсим сетевой диапазон
            if '-' in network_range:
                # Формат: 192.168.1.1-100
                devices = self.ping_range_format(network_range, timeout)
            elif '/' in network_range:
                # Формат CIDR: 192.168.1.0/24
                devices = self.ping_cidr_format(network_range, timeout)
            else:
                # Одиночный IP
                devices = self.ping_single_ip(network_range, timeout)
                
        except Exception as e:
            print(f"Error parsing network range {network_range}: {e}")
            return []
        
        return devices

    def ping_cidr_format(self, cidr_range, timeout=2):
        """Сканирование в формате CIDR"""
        devices = []
        try:
            network = ipaddress.ip_network(cidr_range, strict=False)
            hosts = list(network.hosts())
            total_hosts = len(hosts)
            
            if total_hosts == 0:  # Для /31 и /32 сетей
                hosts = [network.network_address, network.broadcast_address]
                total_hosts = len([h for h in hosts if h is not None])
            
            scanned_hosts = 0
            
            for host in hosts:
                if not self.is_scanning:
                    break
                    
                if host is None:
                    continue
                    
                ip = str(host)
                if self.ping_host(ip, timeout):
                    device_info = self.get_device_info(ip)
                    devices.append(device_info)
                
                scanned_hosts += 1
                self.scan_progress = (scanned_hosts / total_hosts) * 100
                
        except Exception as e:
            print(f"Error in CIDR scan: {e}")
            
        return devices

    def ping_range_format(self, range_str, timeout=2):
        """Сканирование в формате диапазона IP-адресов"""
        devices = []
        
        try:
            # Формат: 192.168.1.1-100
            base_ip, range_part = range_str.split('-')
            ip_parts = base_ip.split('.')
            
            if len(ip_parts) != 4:
                raise ValueError("Invalid IP format")
            
            start_ip = int(ip_parts[3])
            end_ip = int(range_part)
            
            if start_ip > end_ip:
                start_ip, end_ip = end_ip, start_ip
            
            total_ips = end_ip - start_ip + 1
            scanned_ips = 0
            
            for i in range(start_ip, end_ip + 1):
                if not self.is_scanning:
                    break
                    
                ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{i}"
                
                if self.ping_host(ip, timeout):
                    device_info = self.get_device_info(ip)
                    devices.append(device_info)
                
                scanned_ips += 1
                self.scan_progress = (scanned_ips / total_ips) * 100
                
        except Exception as e:
            print(f"Error parsing range format {range_str}: {e}")
        
        return devices

    def ping_single_ip(self, ip, timeout=2):
        """Пинг одиночного IP"""
        devices = []
        if self.ping_host(ip, timeout):
            device_info = self.get_device_info(ip)
            devices.append(device_info)
        return devices

    def ping_host(self, ip, timeout=2):
        """Улучшенная функция ping"""
        try:
            import platform
            # Увеличиваем таймаут и количество попыток
            if platform.system().lower() == "windows":
                param = f"-n 2 -w {timeout * 1000}"
            else:
                param = f"-c 2 -W {timeout}"
                
            command = f"ping {param} {ip}"
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=True,
                timeout=timeout + 1
            )
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            print(f"Ping error for {ip}: {e}")
            return False

    def arp_scan(self, interface=None):
        """
        ARP сканирование локальной сети
        """
        devices = []
        
        try:
            if platform.system().lower() == "windows":
                # Для Windows используем arp -a
                result = subprocess.run(
                    ["arp", "-a"], 
                    capture_output=True, 
                    text=True, 
                    encoding='cp866',
                    timeout=10
                )
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        line = line.strip()
                        if 'dynamic' in line.lower() or 'static' in line.lower():
                            # Парсим строку ARP таблицы
                            parts = line.split()
                            if len(parts) >= 2:
                                ip = parts[0]
                                mac = parts[1]
                                if self.is_valid_ip(ip) and self.is_valid_mac(mac):
                                    device_info = {
                                        'ip_address': ip,
                                        'mac_address': mac,
                                        'hostname': self.get_hostname(ip),
                                        'vendor': self.get_vendor_from_mac(mac),
                                        'os_info': 'Unknown',
                                        'response_time': 0,
                                        'ports': []
                                    }
                                    devices.append(device_info)
            
            else:
                # Для Linux используем arp-scan или ip neighbor
                try:
                    result = subprocess.run(
                        ["arp-scan", "--localnet", "--retry=3", "--timeout=1000"], 
                        capture_output=True, 
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            parts = line.split()
                            if len(parts) >= 2 and self.is_valid_ip(parts[0]):
                                ip = parts[0]
                                mac = parts[1]
                                device_info = {
                                    'ip_address': ip,
                                    'mac_address': mac,
                                    'hostname': self.get_hostname(ip),
                                    'vendor': ' '.join(parts[2:]) if len(parts) > 2 else self.get_vendor_from_mac(mac),
                                    'os_info': 'Unknown',
                                    'response_time': 0,
                                    'ports': []
                                }
                                devices.append(device_info)
                except FileNotFoundError:
                    # Fallback на ip neighbor
                    result = subprocess.run(
                        ["ip", "neighbor", "show"], 
                        capture_output=True, 
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            parts = line.split()
                            if len(parts) >= 5 and "REACHABLE" in line:
                                ip = parts[0]
                                mac = parts[4]
                                device_info = {
                                    'ip_address': ip,
                                    'mac_address': mac,
                                    'hostname': self.get_hostname(ip),
                                    'vendor': self.get_vendor_from_mac(mac),
                                    'os_info': 'Unknown',
                                    'response_time': 0,
                                    'ports': []
                                }
                                devices.append(device_info)
                                
        except Exception as e:
            print(f"ARP scan error: {e}")
            
        return devices

    def get_hostname(self, ip):
        """Получение hostname устройства"""
        try:
            import socket
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return 'Unknown'

    def get_device_info(self, ip):
        """
        Получение информации об устройстве (упрощенная версия)
        """
        return {
            'ip_address': ip,
            'hostname': self.get_hostname(ip),
            'mac_address': 'Unknown',
            'vendor': 'Unknown',
            'os_info': 'Unknown',
            'response_time': 0,
            'ports': []
        }

    def is_valid_ip(self, ip):
        """Проверка валидности IP-адреса"""
        try:
            ipaddress.ip_address(ip)
            return True
        except:
            return False

    def is_valid_mac(self, mac):
        """Проверка валидности MAC-адреса"""
        import re
        mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        return bool(mac_pattern.match(mac))

    def get_vendor_from_mac(self, mac):
        """Определение производителя по MAC"""
        vendors = {
            '00:50:56': 'VMware', '00:0C:29': 'VMware', '00:1C:42': 'Parallels',
            '00:16:3E': 'Xen', '00:15:5D': 'Microsoft Hyper-V', '00:1B:21': 'Cisco',
            '00:1E:68': 'Cisco', '00:24:81': 'Cisco', '00:26:0B': 'Cisco',
            '00:50:BA': 'D-Link', '00:1C:F0': 'Netgear', '00:26:F2': 'Netgear',
            '00:1E:2A': 'TP-Link', '00:1D:0F': 'TP-Link', '00:23:CD': 'TP-Link',
            '00:08:22': 'Samsung', '00:12:FB': 'Samsung', '00:1C:43': 'Samsung',
            '00:26:5C': 'Samsung', '00:E0:4C': 'Realtek', '00:13:D4': 'Realtek',
            '00:14:D1': 'Realtek', '00:17:31': 'ASUS', '00:1D:60': 'ASUS',
            '00:26:18': 'ASUS'
        }
        
        mac_prefix = mac.replace('-', ':').upper()[:8]
        return vendors.get(mac_prefix, 'Unknown')

    def get_local_network(self):
        """Автоматическое определение локальной сети"""
        try:
            # Создаем временное соединение чтобы определить локальный IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            
            # Определяем сеть на основе локального IP
            ip_parts = local_ip.split('.')
            return f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
        except:
            return "192.168.1.0/24"  # Fallback сеть

    def start_scan(self, scan_type, target):
        """
        Запуск сканирования
        """
        self.is_scanning = True
        self.scan_progress = 0
        devices = []
        
        try:
            if scan_type == 'ping':
                print(f"Starting ping scan for: {target}")
                devices = self.ping_sweep(target)
            elif scan_type == 'arp':
                # Если target не указан, определяем локальную сеть автоматически
                if target == 'auto' or not target:
                    target = self.get_local_network()
                    print(f"Auto-detected network: {target}")
                print(f"Starting ARP scan for: {target}")
                devices = self.arp_scan()
            
            self.scan_progress = 100
            print(f"Scan completed. Found {len(devices)} devices.")
            
        except Exception as e:
            print(f"Scan error: {e}")
        finally:
            self.is_scanning = False
            
        return devices

# Глобальный объект сканера
network_scanner = NetworkScanner()
  
class NetworkScanner:
    def __init__(self):
        self.active_devices = []
        self.scan_progress = 0
        self.is_scanning = False
        
    def ping_sweep(self, network_range, timeout=1):
        """
        Ping сканирование сети с поддержкой разных форматов
        """
        devices = []
        
        try:
            # Парсим сетевой диапазон
            if '-' in network_range:
                # Формат: 192.168.1.1-100
                devices = self.ping_range_format(network_range, timeout)
            else:
                # Формат CIDR: 192.168.1.0/24
                devices = self.ping_cidr_format(network_range, timeout)
                
        except Exception as e:
            print(f"Error parsing network range {network_range}: {e}")
            return []
        
        return devices

    def ping_cidr_format(self, cidr_range, timeout=1):
        """Сканирование в формате CIDR"""
        devices = []
        network = ipaddress.ip_network(cidr_range, strict=False)
        total_hosts = len(list(network.hosts()))
        scanned_hosts = 0
        
        def ping_host(ip):
            try:
                param = "-n 1 -w {}".format(timeout * 1000) if platform.system().lower() == "windows" else "-c 1 -W {}".format(timeout)
                command = f"ping {param} {ip}"
                response = subprocess.run(
                    command, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL, 
                    shell=True
                )
                return response.returncode == 0
            except:
                return False
        
        threads = []
        
        def check_host(host):
            if ping_host(str(host)):
                device_info = self.get_device_info(str(host))
                devices.append(device_info)
            
            nonlocal scanned_hosts
            scanned_hosts += 1
            self.scan_progress = (scanned_hosts / total_hosts) * 100
        
        # Сканируем все хосты в сети
        for host in network.hosts():
            if not self.is_scanning:
                break
                
            thread = threading.Thread(target=check_host, args=(host,))
            threads.append(thread)
            thread.start()
            
            # Ограничиваем количество одновременных потоков
            if len(threads) >= 50:
                for t in threads:
                    t.join()
                threads = []
        
        # Ждем завершения оставшихся потоков
        for t in threads:
            t.join()
            
        return devices

    def ping_range_format(self, range_str, timeout=1):
        """Сканирование в формате диапазона IP-адресов"""
        devices = []
        
        try:
            # Формат: 192.168.1.1-100
            base_ip, range_part = range_str.split('-')
            ip_parts = base_ip.split('.')
            
            if len(ip_parts) != 4:
                raise ValueError("Invalid IP format")
            
            start_ip = int(ip_parts[3])
            end_ip = int(range_part)
            
            if start_ip > end_ip:
                start_ip, end_ip = end_ip, start_ip
            
            total_ips = end_ip - start_ip + 1
            scanned_ips = 0
            
            def ping_host(ip):
                try:
                    param = "-n 1 -w {}".format(timeout * 1000) if platform.system().lower() == "windows" else "-c 1 -W {}".format(timeout)
                    command = f"ping {param} {ip}"
                    response = subprocess.run(
                        command, 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL, 
                        shell=True
                    )
                    return response.returncode == 0
                except:
                    return False
            
            threads = []
            
            def check_single_ip(ip):
                if ping_host(ip):
                    device_info = self.get_device_info(ip)
                    devices.append(device_info)
                
                nonlocal scanned_ips
                scanned_ips += 1
                self.scan_progress = (scanned_ips / total_ips) * 100
            
            for i in range(start_ip, end_ip + 1):
                if not self.is_scanning:
                    break
                    
                ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{i}"
                
                thread = threading.Thread(target=check_single_ip, args=(ip,))
                threads.append(thread)
                thread.start()
                
                # Ограничиваем количество одновременных потоков
                if len(threads) >= 50:
                    for t in threads:
                        t.join()
                    threads = []
            
            # Ждем завершения оставшихся потоков
            for t in threads:
                t.join()
                
        except Exception as e:
            print(f"Error parsing range format {range_str}: {e}")
        
        return devices

    def arp_scan(self, interface=None):
        """
        ARP сканирование локальной сети
        """
        devices = []
        
        try:
            if platform.system().lower() == "windows":
                # Для Windows используем arp -a
                result = subprocess.run(
                    ["arp", "-a"], 
                    capture_output=True, 
                    text=True, 
                    encoding='cp866'
                )
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'dynamic' in line.lower() or 'static' in line.lower():
                            parts = line.split()
                            if len(parts) >= 2:
                                ip = parts[0]
                                mac = parts[1]
                                if self.is_valid_ip(ip) and self.is_valid_mac(mac):
                                    device_info = self.get_device_info(ip)
                                    device_info['mac_address'] = mac
                                    device_info['vendor'] = self.get_vendor_from_mac(mac)
                                    devices.append(device_info)
            
            else:
                # Для Linux используем arp-scan или ip neighbor
                try:
                    result = subprocess.run(
                        ["arp-scan", "--localnet"], 
                        capture_output=True, 
                        text=True
                    )
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            parts = line.split()
                            if len(parts) >= 2 and self.is_valid_ip(parts[0]):
                                ip = parts[0]
                                mac = parts[1]
                                device_info = self.get_device_info(ip)
                                device_info['mac_address'] = mac
                                device_info['vendor'] = ' '.join(parts[2:]) if len(parts) > 2 else ''
                                devices.append(device_info)
                except:
                    # Fallback на ip neighbor
                    result = subprocess.run(
                        ["ip", "neighbor", "show"], 
                        capture_output=True, 
                        text=True
                    )
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            parts = line.split()
                            if len(parts) >= 5 and parts[3] == "REACHABLE":
                                ip = parts[0]
                                mac = parts[4]
                                device_info = self.get_device_info(ip)
                                device_info['mac_address'] = mac
                                devices.append(device_info)
                                
        except Exception as e:
            print(f"ARP scan error: {e}")
            
        return devices

    def port_scan(self, ip, ports="21,22,23,80,443,3389,8080"):
        """
        Сканирование портов устройства
        """
        open_ports = []
        
        def check_port(port):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex((ip, port))
                    if result == 0:
                        open_ports.append(port)
            except:
                pass
        
        threads = []
        port_list = [int(p.strip()) for p in ports.split(',')]
        
        for port in port_list:
            if not self.is_scanning:
                break
            thread = threading.Thread(target=check_port, args=(port,))
            threads.append(thread)
            thread.start()
            
        for thread in threads:
            thread.join()
            
        return sorted(open_ports)

    def get_device_info(self, ip):
        """
        Получение информации об устройстве
        """
        device_info = {
            'ip_address': ip,
            'hostname': 'Unknown',
            'mac_address': 'Unknown',
            'vendor': 'Unknown',
            'os_info': 'Unknown',
            'response_time': 0,
            'ports': []
        }
        
        try:
            # Получаем hostname
            try:
                hostname = socket.gethostbyaddr(ip)[0]
                device_info['hostname'] = hostname
            except:
                pass
            
            # Измеряем время ответа
            start_time = time.time()
            param = "-n 1 -w 1000" if platform.system().lower() == "windows" else "-c 1 -W 1"
            result = subprocess.run(
                f"ping {param} {ip}", 
                capture_output=True, 
                shell=True
            )
            end_time = time.time()
            
            if result.returncode == 0:
                device_info['response_time'] = round((end_time - start_time) * 1000, 2)
            
            # Сканируем порты (только основные)
            device_info['ports'] = self.port_scan(ip, "21,22,23,80,443,3389,8080")
            
        except Exception as e:
            print(f"Error getting device info for {ip}: {e}")
        
        return device_info

    def is_valid_ip(self, ip):
        """Проверка валидности IP-адреса"""
        try:
            ipaddress.ip_address(ip)
            return True
        except:
            return False

    def is_valid_mac(self, mac):
        """Проверка валидности MAC-адреса"""
        import re
        mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        return bool(mac_pattern.match(mac))

    def get_vendor_from_mac(self, mac):
        """Определение производителя по MAC (упрощенная версия)"""
        # В реальном приложении можно использовать базу OUI
        vendors = {
            '00:50:56': 'VMware',
            '00:0C:29': 'VMware',
            '00:1C:42': 'Parallels',
            '00:16:3E': 'Xen',
            '00:15:5D': 'Microsoft Hyper-V',
            '00:1B:21': 'Cisco',
            '00:1E:68': 'Cisco',
            '00:24:81': 'Cisco',
            '00:26:0B': 'Cisco',
            '00:50:BA': 'D-Link',
            '00:1C:F0': 'Netgear',
            '00:26:F2': 'Netgear',
            '00:1E:2A': 'TP-Link',
            '00:1D:0F': 'TP-Link',
            '00:23:CD': 'TP-Link',
            '00:08:22': 'Samsung',
            '00:12:FB': 'Samsung',
            '00:1C:43': 'Samsung',
            '00:26:5C': 'Samsung',
            '00:E0:4C': 'Realtek',
            '00:13:D4': 'Realtek',
            '00:14:D1': 'Realtek',
            '00:17:31': 'ASUS',
            '00:1D:60': 'ASUS',
            '00:26:18': 'ASUS'
        }
        
        mac_prefix = mac.replace('-', ':').upper()[:8]
        return vendors.get(mac_prefix, 'Unknown')

    def get_local_network(self):
        """Автоматическое определение локальной сети"""
        try:
            # Создаем временное соединение чтобы определить локальный IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            
            # Определяем сеть на основе локального IP
            ip_parts = local_ip.split('.')
            return f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
        except:
            return "192.168.1.0/24"  # Fallback сеть

    def start_scan(self, scan_type, target):
        """
        Запуск сканирования
        """
        self.is_scanning = True
        self.scan_progress = 0
        devices = []
        
        try:
            if scan_type == 'ping':
                devices = self.ping_sweep(target)
            elif scan_type == 'arp':
                # Если target не указан, определяем локальную сеть автоматически
                if target == 'auto' or not target:
                    target = self.get_local_network()
                    print(f"Auto-detected network: {target}")
                devices = self.arp_scan()
            
            self.scan_progress = 100
            
        except Exception as e:
            print(f"Scan error: {e}")
        finally:
            self.is_scanning = False
            
        return devices