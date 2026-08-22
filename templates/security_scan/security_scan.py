from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from templates.base.requirements import login_required, get_current_user, permissions_required
from templates.roles.permissions import Permissions
from templates.base.database_helper import db
from models import ScanTask, PortResult, Vulnerability, BruteForceResult, WhitelistNetwork, Organization
from datetime import datetime
import subprocess
import threading
import json
import ipaddress
from sqlalchemy import desc

bluprint_security_scan = Blueprint('security_scan', __name__, url_prefix='/security_scan')

# ========== УТИЛИТЫ ==========

def is_target_allowed(target):
    """Проверка, что целевой IP/сеть разрешена в whitelist"""
    try:
        if '/' in target:
            net = ipaddress.ip_network(target, strict=False)
        else:
            net = ipaddress.ip_network(target, strict=False)
        whitelist = WhitelistNetwork.query.filter_by(is_active=True).all()
        for w in whitelist:
            w_net = ipaddress.ip_network(w.network, strict=False)
            if net.subnet_of(w_net):
                return True
        return False
    except:
        return False

def run_scan_task(app, task_id):
    """Фоновая задача сканирования с контекстом приложения"""
    with app.app_context():
        task = ScanTask.query.get(task_id)
        if not task:
            return
        try:
            task.status = 'running'
            db.session.commit()

            if task.scan_type == 'port':
                output = run_nmap(task.target, task.profile)
                parse_nmap_output(task.id, output)
            elif task.scan_type == 'vuln':
                output = run_nikto(task.target)
                parse_nikto_output(task.id, output)
            elif task.scan_type == 'bruteforce':
                output = run_hydra(task.target, task.profile)
                parse_hydra_output(task.id, output)

            task.raw_output = output
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()

def run_nmap(target, profile='default'):
    profiles = {
        'default': '-sT -sV -p- -T4',
        'quick': '-sT -sV -p 21,22,23,80,443,3389,8080 -T4',
        'full': '-sT -sV -p- -sC -A -T4',
        'udp': '-sU -sV -p 1-1000 -T4',
        'script': '-sT -sV --script=vuln -p- -T4'
    }
    flags = profiles.get(profile, profiles['default'])
    cmd = f"nmap {flags} {target}"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            # Если ошибка из-за прав, пробуем альтернативу для SYN-сканирования
            if "requires root privileges" in result.stderr:
                # Заменяем все -sS на -sT, но -sU оставляем
                flags = flags.replace('-sS', '-sT')
                cmd = f"nmap {flags} {target}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)
                if result.returncode != 0:
                    raise Exception(f"nmap error: {result.stderr}")
            else:
                raise Exception(f"nmap error: {result.stderr}")
        return result.stdout
    except FileNotFoundError:
        raise Exception("nmap не установлен. Установите nmap (sudo apt install nmap)")
    except subprocess.TimeoutExpired:
        raise Exception("Сканирование nmap превысило таймаут (1 час)")

def parse_nmap_output(task_id, output):
    import re
    lines = output.split('\n')
    for line in lines:
        match = re.match(r'(\d+)/(tcp|udp)\s+open\s+(\S+)(?:\s+(.*))?', line)
        if match:
            port = int(match.group(1))
            protocol = match.group(2)
            service = match.group(3)
            version = match.group(4) if match.group(4) else ''
            result = PortResult(
                task_id=task_id,
                ip=target_from_output(output),
                port=port,
                protocol=protocol,
                service=service,
                version=version,
                state='open'
            )
            db.session.add(result)
    db.session.commit()

def target_from_output(output):
    import re
    match = re.search(r'Nmap scan report for (\S+)', output)
    if match:
        return match.group(1)
    return 'Unknown'

def run_nikto(target):
    cmd = f"nikto -h {target}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise Exception(f"nikto error: {result.stderr}")
    return result.stdout

def parse_nikto_output(task_id, output):
    import re
    for line in output.split('\n'):
        if '+' in line and ('Vulnerability' in line or 'OSVDB' in line):
            name = line.strip()
            vuln = Vulnerability(
                task_id=task_id,
                source='nikto',
                name=name[:200],
                severity='unknown'
            )
            db.session.add(vuln)
    db.session.commit()

def run_hydra(target, profile):
    service = profile.split(' ')[0] if ' ' in profile else 'ssh'
    cmd = f"hydra -L /usr/share/wordlists/users.txt -P /usr/share/wordlists/passwords.txt {target} {service}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    if result.returncode != 0 and result.returncode != 1:
        raise Exception(f"hydra error: {result.stderr}")
    return result.stdout

def parse_hydra_output(task_id, output):
    import re
    for line in output.split('\n'):
        if 'login:' in line and 'password:' in line:
            parts = line.split()
            username = parts[parts.index('login:')+1]
            password = parts[parts.index('password:')+1]
            result = BruteForceResult(
                task_id=task_id,
                service='ssh',
                target='target',
                username=username,
                password=password,
                source='hydra'
            )
            db.session.add(result)
    db.session.commit()

# ========== МАРШРУТЫ ==========

@bluprint_security_scan.route('/')
@login_required
@permissions_required([Permissions.security_scan_read, Permissions.security_scan_manage])
def index():
    user = get_current_user()
    tasks = ScanTask.query.filter_by(user_id=user.id).order_by(desc(ScanTask.started_at)).limit(20).all()
    orgs = Organization.query.all()
    return render_template('security_scan/index.html', tasks=tasks, orgs=orgs)

@bluprint_security_scan.route('/start', methods=['POST'])
@login_required
@permissions_required([Permissions.security_scan_manage])
def start_scan():
    user = get_current_user()
    scan_type = request.form.get('scan_type')
    target = request.form.get('target')
    name = request.form.get('name', f'{scan_type} scan - {datetime.now()}')
    profile = request.form.get('profile', 'default')
    org_id = request.form.get('organization_id')
    if org_id and org_id.isdigit():
        org_id = int(org_id)
    else:
        org_id = None

    if not is_target_allowed(target):
        flash('Цель не входит в разрешённый whitelist', 'error')
        return redirect(url_for('security_scan.index'))

    task = ScanTask(
        name=name,
        scan_type=scan_type,
        target=target,
        profile=profile,
        status='pending',
        user_id=user.id,
        organization_id=org_id
    )
    db.session.add(task)
    db.session.commit()

    # Передаём app в фоновый поток
    app = current_app._get_current_object()
    thread = threading.Thread(target=run_scan_task, args=(app, task.id))
    thread.daemon = True
    thread.start()

    flash('Сканирование запущено', 'success')
    return redirect(url_for('security_scan.index'))

@bluprint_security_scan.route('/task/<int:task_id>')
@login_required
@permissions_required([Permissions.security_scan_read, Permissions.security_scan_manage])
def task_detail(task_id):
    user = get_current_user()
    task = ScanTask.query.get_or_404(task_id)
    return render_template('security_scan/task_detail.html', task=task)

@bluprint_security_scan.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
@permissions_required([Permissions.security_scan_manage])
def delete_task(task_id):
    user = get_current_user()
    task = ScanTask.query.get_or_404(task_id)

    db.session.delete(task)
    db.session.commit()
    flash('Задача удалена', 'success')
    return redirect(url_for('security_scan.index'))

@bluprint_security_scan.route('/whitelist', methods=['GET', 'POST'])
@login_required
@permissions_required([Permissions.security_scan_whitelist])
def whitelist():
    if request.method == 'POST':
        network = request.form.get('network')
        description = request.form.get('description')
        if network:
            try:
                ipaddress.ip_network(network, strict=False)
                wl = WhitelistNetwork(network=network, description=description)
                db.session.add(wl)
                db.session.commit()
                flash('Сеть добавлена в whitelist', 'success')
            except:
                flash('Неверный формат сети', 'error')
    whitelist = WhitelistNetwork.query.all()
    return render_template('security_scan/whitelist.html', whitelist=whitelist)

@bluprint_security_scan.route('/whitelist/<int:wl_id>/delete', methods=['POST'])
@login_required
@permissions_required([Permissions.security_scan_whitelist])
def delete_whitelist(wl_id):
    wl = WhitelistNetwork.query.get_or_404(wl_id)
    db.session.delete(wl)
    db.session.commit()
    flash('Запись удалена', 'success')
    return redirect(url_for('security_scan.whitelist'))