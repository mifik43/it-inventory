import subprocess
import ipaddress
import platform
import socket
import threading
import time
from datetime import datetime, timedelta
import json
from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, current_app
from templates.base.database_helper import db
from templates.base.requirements import permissions_required
from templates.roles.permissions import Permissions
from models import NetworkScan, NetworkDevice, Organization, NetworkGraph, NetworkGraphDevice
from sqlalchemy import desc, func

bluprint_network_scan_routes = Blueprint("network_scan", __name__)

# ========== УТИЛИТЫ ==========

def validate_network_range(network_range):
    try:
        if '/' in network_range:
            ipaddress.ip_network(network_range, strict=False)
            return True
        if '-' in network_range:
            base_ip, end = network_range.split('-')
            ipaddress.ip_address(base_ip)
            end_ip = int(end)
            return 1 <= end_ip <= 255
        ipaddress.ip_address(network_range)
        return True
    except:
        return False

def get_port_service(port):
    port_services = {
        21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
        80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS', 993: 'IMAPS',
        995: 'POP3S', 1433: 'MSSQL', 1521: 'Oracle', 3306: 'MySQL',
        3389: 'RDP', 5432: 'PostgreSQL', 5900: 'VNC', 8080: 'HTTP-Alt'
    }
    return port_services.get(port, 'Unknown')

# ========== КЛАСС СКАНЕРА ==========

class NetworkScanner:
    def __init__(self):
        self.is_scanning = False
        self.scan_progress = 0

    def ping_sweep(self, network_range, timeout=2):
        devices = []
        try:
            if '-' in network_range:
                devices = self._ping_range_format(network_range, timeout)
            elif '/' in network_range:
                devices = self._ping_cidr_format(network_range, timeout)
            else:
                devices = self._ping_single_ip(network_range, timeout)
        except Exception as e:
            print(f"Error scanning {network_range}: {e}")
        return devices

    def _ping_cidr_format(self, cidr_range, timeout=2):
        devices = []
        network = ipaddress.ip_network(cidr_range, strict=False)
        hosts = list(network.hosts())
        total = len(hosts)
        scanned = 0
        threads = []
        results = []

        def check_host(host):
            ip = str(host)
            if self._ping_host(ip, timeout):
                info = self._get_device_info(ip)
                results.append(info)
            nonlocal scanned
            scanned += 1
            self.scan_progress = (scanned / total) * 100 if total else 0

        for host in hosts:
            if not self.is_scanning:
                break
            t = threading.Thread(target=check_host, args=(host,))
            threads.append(t)
            t.start()
            if len(threads) >= 50:
                for t in threads:
                    t.join()
                threads = []

        for t in threads:
            t.join()
        return results

    def _ping_range_format(self, range_str, timeout=2):
        devices = []
        base_ip, range_part = range_str.split('-')
        ip_parts = base_ip.split('.')
        if len(ip_parts) != 4:
            raise ValueError("Invalid IP format")
        start_ip = int(ip_parts[3])
        end_ip = int(range_part)
        if start_ip > end_ip:
            start_ip, end_ip = end_ip, start_ip
        total = end_ip - start_ip + 1
        scanned = 0
        threads = []
        results = []

        def check_ip(i):
            ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{i}"
            if self._ping_host(ip, timeout):
                info = self._get_device_info(ip)
                results.append(info)
            nonlocal scanned
            scanned += 1
            self.scan_progress = (scanned / total) * 100 if total else 0

        for i in range(start_ip, end_ip + 1):
            if not self.is_scanning:
                break
            t = threading.Thread(target=check_ip, args=(i,))
            threads.append(t)
            t.start()
            if len(threads) >= 50:
                for t in threads:
                    t.join()
                threads = []

        for t in threads:
            t.join()
        return results

    def _ping_single_ip(self, ip, timeout=2):
        if self._ping_host(ip, timeout):
            return [self._get_device_info(ip)]
        return []

    def _ping_host(self, ip, timeout=2):
        try:
            if platform.system().lower() == "windows":
                param = f"-n 2 -w {timeout * 1000}"
            else:
                param = f"-c 2 -W {timeout}"
            command = f"ping {param} {ip}"
            result = subprocess.run(command, capture_output=True, text=True, shell=True, timeout=timeout + 1)
            return result.returncode == 0
        except:
            return False

    def _get_device_info(self, ip):
        info = {
            'ip_address': ip,
            'hostname': 'Unknown',
            'mac_address': 'Unknown',
            'vendor': 'Unknown',
            'os_info': 'Unknown',
            'response_time': 0,
            'ports': []
        }
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            info['hostname'] = hostname
        except:
            pass
        mac = self._get_mac_from_arp(ip)
        if mac:
            info['mac_address'] = mac
            info['vendor'] = self._get_vendor_from_mac(mac)
        
        # Определение ОС по TTL
        try:
            if platform.system().lower() == "windows":
                result = subprocess.run(["ping", "-n", "1", "-w", "1000", ip], capture_output=True, text=True, timeout=2)
            else:
                result = subprocess.run(["ping", "-c", "1", "-W", "1", ip], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                import re
                match = re.search(r'ttl=(\d+)', result.stdout, re.IGNORECASE)
                if match:
                    ttl = int(match.group(1))
                    if ttl <= 64:
                        info['os_info'] = 'Linux/Unix'
                    elif ttl <= 128:
                        info['os_info'] = 'Windows'
                    else:
                        info['os_info'] = 'Unknown'
        except:
            pass

        start = time.time()
        if self._ping_host(ip, 1):
            info['response_time'] = round((time.time() - start) * 1000, 2)
        info['ports'] = self._port_scan(ip, "21,22,23,80,443,3389,8080")
        return info

    def _get_mac_from_arp(self, ip):
        try:
            if platform.system().lower() == "windows":
                result = subprocess.run(["arp", "-a", ip], capture_output=True, text=True, timeout=5)
                for line in result.stdout.split('\n'):
                    if ip in line and ('dynamic' in line.lower() or 'static' in line.lower()):
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[1]
            else:
                result = subprocess.run(["ip", "neighbor", "show", ip], capture_output=True, text=True, timeout=5)
                for line in result.stdout.split('\n'):
                    if ip in line and 'REACHABLE' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            return parts[4]
        except:
            pass
        return None

    def _get_vendor_from_mac(self, mac):
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

    def _port_scan(self, ip, ports_str):
        open_ports = []
        port_list = [int(p.strip()) for p in ports_str.split(',')]
        for port in port_list:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.5)
                    if sock.connect_ex((ip, port)) == 0:
                        open_ports.append(port)
            except:
                pass
        return open_ports

    def arp_scan(self):
        devices = []
        try:
            if platform.system().lower() == "windows":
                result = subprocess.run(["arp", "-a"], capture_output=True, text=True, encoding='cp866', timeout=10)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'dynamic' in line.lower() or 'static' in line.lower():
                            parts = line.split()
                            if len(parts) >= 2:
                                ip = parts[0]
                                mac = parts[1]
                                if self._is_valid_ip(ip) and self._is_valid_mac(mac):
                                    info = self._get_device_info(ip)
                                    info['mac_address'] = mac
                                    info['vendor'] = self._get_vendor_from_mac(mac)
                                    devices.append(info)
            else:
                try:
                    result = subprocess.run(["arp-scan", "--localnet", "--retry=3", "--timeout=1000"], capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            parts = line.split()
                            if len(parts) >= 2 and self._is_valid_ip(parts[0]):
                                ip = parts[0]
                                mac = parts[1]
                                info = self._get_device_info(ip)
                                info['mac_address'] = mac
                                info['vendor'] = ' '.join(parts[2:]) if len(parts) > 2 else self._get_vendor_from_mac(mac)
                                devices.append(info)
                except FileNotFoundError:
                    result = subprocess.run(["ip", "neighbor", "show"], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'REACHABLE' in line:
                                parts = line.split()
                                if len(parts) >= 5:
                                    ip = parts[0]
                                    mac = parts[4]
                                    info = self._get_device_info(ip)
                                    info['mac_address'] = mac
                                    info['vendor'] = self._get_vendor_from_mac(mac)
                                    devices.append(info)
        except Exception as e:
            print(f"ARP scan error: {e}")
        return devices

    def _is_valid_ip(self, ip):
        try:
            ipaddress.ip_address(ip)
            return True
        except:
            return False

    def _is_valid_mac(self, mac):
        import re
        return bool(re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac))

    def get_local_network(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            ip_parts = local_ip.split('.')
            return f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
        except:
            return "192.168.1.0/24"

    def start_scan(self, scan_type, target):
        self.is_scanning = True
        self.scan_progress = 0
        devices = []
        try:
            if scan_type == 'ping':
                devices = self.ping_sweep(target)
            elif scan_type == 'arp':
                if target == 'auto' or not target:
                    target = self.get_local_network()
                devices = self.arp_scan()
            self.scan_progress = 100
        except Exception as e:
            print(f"Scan error: {e}")
        finally:
            self.is_scanning = False
        return devices

network_scanner = NetworkScanner()

# ========== ФУНКЦИЯ ФОНОВОГО СКАНИРОВАНИЯ ==========

def run_network_scan_background(app, scan_id, scan_type, target_range):
    with app.app_context():
        try:
            devices = network_scanner.start_scan(scan_type, target_range)
            for device in devices:
                net_device = NetworkDevice(
                    scan_id=scan_id,
                    ip_address=device['ip_address'],
                    mac_address=device.get('mac_address', 'Unknown'),
                    hostname=device.get('hostname', 'Unknown'),
                    vendor=device.get('vendor', 'Unknown'),
                    os_info=device.get('os_info', 'Unknown'),
                    ports=json.dumps(device.get('ports', [])),
                    response_time=device.get('response_time', 0),
                    last_seen=datetime.utcnow()
                )
                db.session.add(net_device)

            scan = NetworkScan.query.get(scan_id)
            scan.status = 'completed'
            scan.devices_found = len(devices)
            scan.completed_at = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            scan = NetworkScan.query.get(scan_id)
            scan.status = 'failed'
            scan.notes = str(e)
            db.session.commit()

# ========== МАРШРУТЫ ==========

@bluprint_network_scan_routes.route('/network_scan')
@permissions_required(Permissions.guest_wifi_manage)
def network_scan():
    scans = NetworkScan.query.order_by(desc(NetworkScan.created_at)).limit(10).all()
    organizations = Organization.query.order_by(Organization.name).all()
    return render_template('network_scan/network_scan.html', scans=scans, organizations=organizations)

@bluprint_network_scan_routes.route('/network_scan/start', methods=['POST'])
@permissions_required(Permissions.guest_wifi_manage)
def start_network_scan():
    scan_type = request.form.get('scan_type')
    target_range = request.form.get('target_range')
    scan_name = request.form.get('scan_name', f'Scan {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    organization_id = request.form.get('organization_id')
    if organization_id and organization_id.isdigit():
        organization_id = int(organization_id)
    else:
        organization_id = None

    if scan_type == 'ping' and not target_range:
        flash('Для ping-сканирования необходимо указать сетевой диапазон', 'error')
        return redirect(url_for('network_scan.network_scan'))

    if scan_type == 'ping' and not validate_network_range(target_range):
        flash('Неверный формат сетевого диапазона. Примеры: 192.168.1.0/24, 192.168.1.1-100, 192.168.1.1', 'error')
        return redirect(url_for('network_scan.network_scan'))

    if scan_type == 'arp' and not target_range:
        target_range = 'auto'

    try:
        scan = NetworkScan(
            name=scan_name,
            scan_type=scan_type,
            target_range=target_range,
            status='running',
            organization_id=organization_id
        )
        db.session.add(scan)
        db.session.commit()
        scan_id = scan.id

        app = current_app._get_current_object()
        thread = threading.Thread(
            target=run_network_scan_background,
            args=(app, scan_id, scan_type, target_range)
        )
        thread.daemon = True
        thread.start()
        flash('Сканирование сети запущено!', 'success')
    except Exception as e:
        flash(f'Ошибка при запуске сканирования: {str(e)}', 'error')

    return redirect(url_for('network_scan.network_scan'))

@bluprint_network_scan_routes.route('/network_scan/delete_old', methods=['POST'])
@permissions_required(Permissions.guest_wifi_manage)
def delete_old_scans():
    days = request.form.get('days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    old_scans = NetworkScan.query.filter(NetworkScan.created_at < cutoff).all()
    count = len(old_scans)
    
    if count == 0:
        flash(f'Нет сканирований старше {days} дней', 'info')
        return redirect(url_for('network_scan.network_scan'))
    
    for scan in old_scans:
        NetworkDevice.query.filter_by(scan_id=scan.id).delete()
        db.session.delete(scan)
    db.session.commit()
    
    flash(f'Удалено {count} сканирований старше {days} дней', 'success')
    return redirect(url_for('network_scan.network_scan'))

@bluprint_network_scan_routes.route('/network_scan/<int:scan_id>')
@permissions_required(Permissions.guest_wifi_manage)
def network_scan_results(scan_id):
    scan = NetworkScan.query.get_or_404(scan_id)
    devices = NetworkDevice.query.filter_by(scan_id=scan_id).order_by(NetworkDevice.ip_address).all()
    processed = []
    for d in devices:
        d_dict = d.__dict__
        if d_dict.get('ports'):
            try:
                d_dict['ports'] = json.loads(d_dict['ports'])
            except:
                d_dict['ports'] = []
        processed.append(d_dict)
    return render_template('network_scan/scan_results.html', scan=scan, devices=processed)

@bluprint_network_scan_routes.route('/network_scan/progress')
@permissions_required(Permissions.guest_wifi_manage)
def network_scan_progress():
    return jsonify({
        'is_scanning': network_scanner.is_scanning,
        'progress': network_scanner.scan_progress
    })

@bluprint_network_scan_routes.route('/network_scan/stop', methods=['POST'])
@permissions_required(Permissions.guest_wifi_manage)
def stop_network_scan():
    network_scanner.is_scanning = False
    flash('Сканирование остановлено', 'info')
    return redirect(url_for('network_scan.network_scan'))

@bluprint_network_scan_routes.route('/network_devices')
@permissions_required(Permissions.guest_wifi_manage)
def network_devices():
    devices = db.session.query(NetworkDevice, NetworkScan.name.label('scan_name')).join(
        NetworkScan, NetworkDevice.scan_id == NetworkScan.id
    ).order_by(desc(NetworkDevice.last_seen)).all()

    processed = []
    vendors = set()
    for dev, scan_name in devices:
        d_dict = dev.__dict__
        if d_dict.get('ports'):
            try:
                d_dict['ports'] = json.loads(d_dict['ports'])
            except:
                d_dict['ports'] = []
        d_dict['scan_name'] = scan_name
        processed.append(d_dict)
        if dev.vendor != 'Unknown':
            vendors.add(dev.vendor)

    scans_count = NetworkScan.query.count()
    last_scan = NetworkScan.query.order_by(desc(NetworkScan.created_at)).first()
    last_scan_date = last_scan.created_at.strftime('%Y-%m-%d') if last_scan else 'Нет данных'

    return render_template('network_scan/devices_list.html',
                           devices=processed,
                           vendors_count=len(vendors),
                           scans_count=scans_count,
                           last_scan_date=last_scan_date)

@bluprint_network_scan_routes.route('/network_scan/delete/<int:scan_id>')
@permissions_required(Permissions.guest_wifi_manage)
def delete_network_scan(scan_id):
    scan = NetworkScan.query.get_or_404(scan_id)
    
    # Найти все устройства этого сканирования
    devices = NetworkDevice.query.filter_by(scan_id=scan_id).all()
    
    # Для каждого устройства удалить связанные записи в графах
    for device in devices:
        NetworkGraphDevice.query.filter_by(device_id=device.id).delete()
    
    # Теперь можно удалить устройства и сканирование
    NetworkDevice.query.filter_by(scan_id=scan_id).delete()
    db.session.delete(scan)
    db.session.commit()
    
    flash('Сканирование и все связанные устройства удалены!', 'success')
    return redirect(url_for('network_scan.network_scan'))

@bluprint_network_scan_routes.route('/network_scan/ping/<ip>')
@permissions_required(Permissions.guest_wifi_manage)
def ping_device(ip):
    try:
        param = "-n 1 -w 2000" if platform.system().lower() == "windows" else "-c 1 -W 2"
        command = f"ping {param} {ip}"
        start_time = time.time()
        result = subprocess.run(command, capture_output=True, text=True, shell=True, timeout=5)
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
@permissions_required(Permissions.guest_wifi_manage)
def device_info(device_id):
    device = NetworkDevice.query.get_or_404(device_id)
    d_dict = device.__dict__
    if d_dict.get('ports'):
        try:
            d_dict['ports'] = json.loads(d_dict['ports'])
        except:
            d_dict['ports'] = []
    return jsonify({'success': True, 'device': d_dict})

@bluprint_network_scan_routes.route('/network_scan/delete_device/<int:device_id>', methods=['POST'])
@permissions_required(Permissions.guest_wifi_manage)
def delete_device(device_id):
    device = NetworkDevice.query.get_or_404(device_id)
    db.session.delete(device)
    db.session.commit()
    return jsonify({'success': True})

# ========== МАРШРУТЫ ДЛЯ ГРАФОВ ==========

@bluprint_network_scan_routes.route('/network_graph')
@permissions_required(Permissions.guest_wifi_manage)
def graph_list():
    graphs = NetworkGraph.query.all()
    organizations = Organization.query.all()
    return render_template('network_scan/graph_list.html', graphs=graphs, organizations=organizations)

@bluprint_network_scan_routes.route('/network_graph/create', methods=['GET', 'POST'])
@permissions_required(Permissions.guest_wifi_manage)
def create_graph():
    if request.method == 'POST':
        name = request.form.get('name')
        org_id = request.form.get('organization_id')
        description = request.form.get('description')
        if not name:
            flash('Название графа обязательно', 'error')
            return redirect(url_for('network_scan.create_graph'))
        graph = NetworkGraph(
            name=name,
            organization_id=org_id or None,
            description=description
        )
        db.session.add(graph)
        db.session.commit()
        flash('Граф создан', 'success')
        return redirect(url_for('network_scan.graph_list'))
    organizations = Organization.query.all()
    return render_template('network_scan/create_graph.html', organizations=organizations)

@bluprint_network_scan_routes.route('/network_graph/<int:graph_id>')
@permissions_required(Permissions.guest_wifi_manage)
def view_graph(graph_id):
    import json
    graph = NetworkGraph.query.get_or_404(graph_id)
    devices = [entry.device for entry in graph.devices.all()]
    scans = NetworkScan.query.order_by(desc(NetworkScan.created_at)).all()
    
    # Сериализуемые данные для визуализации
    devices_json = []
    for device in devices:
        # Получаем комментарий из первой записи graph_entries (если есть)
        comment = ''
        if device.graph_entries and device.graph_entries[0]:
            comment = device.graph_entries[0].comment or ''
        device_dict = {
            'id': device.id,
            'ip_address': device.ip_address,
            'hostname': device.hostname or 'Unknown',
            'vendor': device.vendor or 'Unknown',
            'os_info': device.os_info or 'Unknown',
            'mac_address': device.mac_address or 'Unknown',
            'response_time': device.response_time or 0,
            'ports': json.loads(device.ports) if device.ports else [],
            'comment': comment
        }
        devices_json.append(device_dict)
    
    return render_template('network_scan/view_graph.html', 
                         graph=graph, 
                         devices=devices, 
                         devices_json=devices_json, 
                         scans=scans)

@bluprint_network_scan_routes.route('/network_graph/<int:graph_id>/add_scan', methods=['POST'])
@permissions_required(Permissions.guest_wifi_manage)
def add_scan_to_graph(graph_id):
    scan_id = request.form.get('scan_id')
    if not scan_id:
        flash('Не выбрано сканирование', 'error')
        return redirect(url_for('network_scan.view_graph', graph_id=graph_id))
    
    scan = NetworkScan.query.get(scan_id)
    if not scan:
        flash('Сканирование не найдено', 'error')
        return redirect(url_for('network_scan.view_graph', graph_id=graph_id))
    
    graph = NetworkGraph.query.get_or_404(graph_id)
    devices = NetworkDevice.query.filter_by(scan_id=scan_id).all()
    added = 0
    for device in devices:
        existing = NetworkGraphDevice.query.filter_by(graph_id=graph_id, device_id=device.id).first()
        if not existing:
            entry = NetworkGraphDevice(graph_id=graph_id, device_id=device.id)
            db.session.add(entry)
            added += 1
    
    db.session.commit()
    flash(f'Добавлено {added} устройств в граф', 'success')
    return redirect(url_for('network_scan.view_graph', graph_id=graph_id))

@bluprint_network_scan_routes.route('/network_graph/<int:graph_id>/remove_device/<int:device_id>', methods=['POST'])
@permissions_required(Permissions.guest_wifi_manage)
def remove_device_from_graph(graph_id, device_id):
    entry = NetworkGraphDevice.query.filter_by(graph_id=graph_id, device_id=device_id).first()
    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash('Устройство удалено из графа', 'success')
    else:
        flash('Устройство не найдено в графе', 'error')
    return redirect(url_for('network_scan.view_graph', graph_id=graph_id))

@bluprint_network_scan_routes.route('/network_graph/<int:graph_id>/delete', methods=['POST'])
@permissions_required(Permissions.guest_wifi_manage)
def delete_graph(graph_id):
    graph = NetworkGraph.query.get_or_404(graph_id)
    db.session.delete(graph)
    db.session.commit()
    flash('Граф удален', 'success')
    return redirect(url_for('network_scan.graph_list'))

@bluprint_network_scan_routes.route('/network_graph/<int:graph_id>/data')
@permissions_required(Permissions.guest_wifi_manage)
def graph_data(graph_id):
    graph = NetworkGraph.query.get_or_404(graph_id)
    entries = graph.devices.all()
    devices = [entry.device for entry in entries]
    
    nodes = []
    edges = []
    node_ids = set()
    
    for device in devices:
        node_id = device.id
        node_ids.add(node_id)
        label = device.hostname if device.hostname != 'Unknown' else device.ip_address
        nodes.append({
            'id': node_id,
            'label': label,
            'title': f"{device.ip_address}<br>{device.vendor or 'Unknown'}",
            'shape': 'dot',
            'size': 10,
            'color': '#1f78b4'
        })
    
    # Строим связи между устройствами из одного сканирования
    scan_groups = {}
    for device in devices:
        scan_id = device.scan_id
        if scan_id not in scan_groups:
            scan_groups[scan_id] = []
        scan_groups[scan_id].append(device.id)
    
    for scan_id, dev_ids in scan_groups.items():
        if len(dev_ids) > 1:
            for i in range(len(dev_ids)):
                for j in range(i+1, len(dev_ids)):
                    edges.append({
                        'from': dev_ids[i],
                        'to': dev_ids[j],
                        'title': f'Общее сканирование #{scan_id}'
                    })
    
    return jsonify({'nodes': nodes, 'edges': edges})

@bluprint_network_scan_routes.route('/network_graph/<int:graph_id>/device/<int:device_id>/comment', methods=['POST'])
@permissions_required(Permissions.guest_wifi_manage)
def update_device_comment(graph_id, device_id):
    data = request.get_json()
    comment = data.get('comment', '')
    entry = NetworkGraphDevice.query.filter_by(graph_id=graph_id, device_id=device_id).first()
    if not entry:
        return jsonify({'error': 'Устройство не найдено в графе'}), 404
    entry.comment = comment
    db.session.commit()
    return jsonify({'success': True, 'comment': comment})

# ========== КОНТЕКСТНЫЙ ПРОЦЕССОР ==========
@bluprint_network_scan_routes.context_processor
def utility_processor():
    return dict(get_port_service=get_port_service)