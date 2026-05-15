from logger import logger

from flask import render_template, request, redirect, url_for, flash, session, Blueprint, Response, send_file
from datetime import datetime
from templates.base.database import get_db
from templates.base.requirements import permissions_required, permissions_required_all, permissions_required
from templates.roles.permissions import Permissions
from sqlalchemy import text, func, case, or_

from models import WtwareConfig, WtwareDeployment, Script, ScriptResult

# Импорт вспомогательных модулей
from wtware_client import WTwareClient, generate_wtware_config, test_wtware_connection, upload_config_to_wtware
from wtware_ssh import WTwareSSHClient
from excel_utils import export_to_excel, import_from_excel

bluprint_wtware_routes = Blueprint("wtware", __name__)


# ========== МАРШРУТЫ ДЛЯ WTWARE ==========

@bluprint_wtware_routes.route('/wtware')
def wtware_list():
    logger.info("Запуск wtware_list")
    db = get_db()

    try:
        query = db.query(WtwareConfig).order_by(WtwareConfig.name, WtwareConfig.created_at.desc())
        configs = query.all()

        logger.info("Найдено конфигураций WTware: %d", len(configs))
        return render_template('wtware/wtware_list.html', configs=configs)

    except Exception as e:
        logger.error("Ошибка в wtware_list: %s", str(e), exc_info=True)
        flash(f'Ошибка при загрузке конфигураций: {str(e)}', 'error')
        return render_template('wtware/wtware_list.html', configs=[])


@bluprint_wtware_routes.route('/add_wtware', methods=['GET', 'POST'])
def add_wtware():
    logger.info("Запуск add_wtware, метод=%s", request.method)
    db = get_db()

    if request.method == 'POST':
        logger.debug("Данные формы: name=%s, version=%s, server_ip=%s, status=%s",
                      request.form.get('name', ''), request.form.get('version', ''),
                      request.form.get('server_ip', ''), request.form.get('status', ''))

        name = request.form['name']
        version = request.form.get('version', '')
        server_ip = request.form.get('server_ip', '')
        server_port = request.form.get('server_port', 80)
        screen_width = request.form.get('screen_width', 1024)
        screen_height = request.form.get('screen_height', 768)
        auto_start = request.form.get('auto_start', '')
        network_drive = request.form.get('network_drive', '')
        printer_config = request.form.get('printer_config', '')
        startup_script = request.form.get('startup_script', '')
        shutdown_script = request.form.get('shutdown_script', '')
        custom_config = request.form.get('custom_config', '')
        status = request.form.get('status', 'Активна')
        notes = request.form.get('notes', '')

        # Валидация
        if not name:
            logger.warning("Валидация не пройдена: пустой name")
            flash('Название конфигурации обязательно', 'error')
            return render_template('wtware/add_wtware.html')

        try:
            logger.info("Создание новой конфигурации WTware: name=%s, status=%s",
                         name, status)
            config = WtwareConfig(
                name=name,
                version=version,
                server_ip=server_ip,
                server_port=int(server_port) if server_port else 80,
                screen_width=int(screen_width) if screen_width else 1024,
                screen_height=int(screen_height) if screen_height else 768,
                auto_start=auto_start or None,
                network_drive=network_drive or None,
                printer_config=printer_config or None,
                startup_script=startup_script or None,
                shutdown_script=shutdown_script or None,
                custom_config=custom_config or None,
                status=status,
                notes=notes or None,
            )
            db.add(config)
            db.commit()
            logger.info("Конфигурация WTware добавлена успешно, id=%s name=%s",
                         config.id, config.name)
            flash('Конфигурация WTware успешно добавлена!', 'success')
            return redirect(url_for('wtware.wtware_list'))

        except Exception as e:
            db.rollback()
            logger.error("Ошибка при добавлении конфигурации WTware: %s", str(e), exc_info=True)
            flash(f'Ошибка при добавлении конфигурации: {str(e)}', 'error')

    logger.debug("Рендер формы добавления конфигурации WTware")
    return render_template('wtware/add_wtware.html')


@bluprint_wtware_routes.route('/edit_wtware/<int:config_id>', methods=['GET', 'POST'])
def edit_wtware(config_id):
    logger.info("Запуск edit_wtware, config_id=%s, метод=%s", config_id, request.method)
    db = get_db()

    try:
        wtware_config = db.query(WtwareConfig).filter(WtwareConfig.id == config_id).first()

        if not wtware_config:
            logger.warning("Конфигурация не найдена: config_id=%s", config_id)
            flash('Конфигурация не найдена', 'error')
            return redirect(url_for('wtware.wtware_list'))

        if request.method == 'POST':
            logger.debug("Данные формы редактирования: config_id=%s, name=%s, version=%s, status=%s",
                         config_id,
                         request.form.get('name', ''), request.form.get('version', ''),
                         request.form.get('status', ''))

            name = request.form['name']
            version = request.form.get('version', '')
            server_ip = request.form.get('server_ip', '')
            server_port = request.form.get('server_port', 80)
            screen_width = request.form.get('screen_width', 1024)
            screen_height = request.form.get('screen_height', 768)
            auto_start = request.form.get('auto_start', '')
            network_drive = request.form.get('network_drive', '')
            printer_config = request.form.get('printer_config', '')
            startup_script = request.form.get('startup_script', '')
            shutdown_script = request.form.get('shutdown_script', '')
            custom_config = request.form.get('custom_config', '')
            status = request.form.get('status', 'Активна')
            notes = request.form.get('notes', '')

            # Валидация
            if not name:
                logger.warning("Валидация не пройдена при редактировании: пустой name")
                flash('Название конфигурации обязательно', 'error')
                return render_template('wtware/edit_wtware.html', wtware_config=wtware_config)

            try:
                logger.info("Обновление конфигурации WTware: config_id=%s, name=%s, status=%s",
                             config_id, name, status)
                db.query(WtwareConfig).filter(WtwareConfig.id == config_id).update({
                    WtwareConfig.name: name,
                    WtwareConfig.version: version,
                    WtwareConfig.server_ip: server_ip,
                    WtwareConfig.server_port: int(server_port) if server_port else 80,
                    WtwareConfig.screen_width: int(screen_width) if screen_width else 1024,
                    WtwareConfig.screen_height: int(screen_height) if screen_height else 768,
                    WtwareConfig.auto_start: auto_start or None,
                    WtwareConfig.network_drive: network_drive or None,
                    WtwareConfig.printer_config: printer_config or None,
                    WtwareConfig.startup_script: startup_script or None,
                    WtwareConfig.shutdown_script: shutdown_script or None,
                    WtwareConfig.custom_config: custom_config or None,
                    WtwareConfig.status: status,
                    WtwareConfig.notes: notes or None,
                    WtwareConfig.updated_at: func.now(),
                })
                db.commit()
                logger.info("Конфигурация WTware обновлена успешно: config_id=%s", config_id)
                flash('Конфигурация WTware успешно обновлена!', 'success')
                return redirect(url_for('wtware.wtware_list'))

            except Exception as e:
                db.rollback()
                logger.error("Ошибка при обновлении конфигурации WTware config_id=%s: %s",
                              config_id, str(e), exc_info=True)
                flash(f'Ошибка при обновлении конфигурации: {str(e)}', 'error')

        logger.debug("Рендер формы редактирования конфигурации WTware: config_id=%s", config_id)
        return render_template('wtware/edit_wtware.html', wtware_config=wtware_config)

    except Exception as e:
        logger.error("Ошибка в edit_wtware для config_id=%s: %s", config_id, str(e), exc_info=True)
        flash(f'Ошибка при загрузке конфигурации: {str(e)}', 'error')
        return redirect(url_for('wtware.wtware_list'))


@bluprint_wtware_routes.route('/delete_wtware/<int:config_id>')
def delete_wtware(config_id):
    logger.info("Запуск delete_wtware, config_id=%s", config_id)
    db = get_db()

    try:
        db.query(WtwareConfig).filter(WtwareConfig.id == config_id).delete()
        db.commit()
        logger.info("Конфигурация WTware удалена успешно: config_id=%s", config_id)
        flash('Конфигурация WTware успешно удалена!', 'success')
    except Exception as e:
        db.rollback()
        logger.error("Ошибка при удалении конфигурации WTware config_id=%s: %s",
                      config_id, str(e), exc_info=True)
        flash(f'Ошибка при удалении конфигурации: {str(e)}', 'error')

    return redirect(url_for('wtware.wtware_list'))


@bluprint_wtware_routes.route('/wtware_search')
def wtware_search():
    query = request.args.get('q', '')
    logger.info("Запуск wtware_search, query=%s", query)
    db = get_db()

    try:
        patterns = [f'%{query}%']
        configs = db.query(WtwareConfig).filter(
            or_(
                WtwareConfig.name.ilike(patterns[0]),
                WtwareConfig.server_ip.ilike(patterns[0]),
                WtwareConfig.version.ilike(patterns[0]),
                WtwareConfig.notes.ilike(patterns[0]),
            )
        ).order_by(WtwareConfig.name, WtwareConfig.created_at.desc()).all()

        logger.info("Найдено конфигураций по запросу '%s': %d", query, len(configs))
        return render_template('wtware/wtware_list.html', configs=configs, search_query=query)

    except Exception as e:
        logger.error("Ошибка при поиске конфигураций WTware: %s", str(e), exc_info=True)
        flash(f'Ошибка при поиске: {str(e)}', 'error')
        return render_template('wtware/wtware_list.html', configs=[], search_query=query)


# ========== ЭКСПОРТ / ИМПОРТ ==========

@bluprint_wtware_routes.route('/export/wtware')
def export_wtware():
    """Экспорт конфигураций WTware в Excel"""
    logger.info("Запуск wtware_export")
    try:
        excel_file = export_to_excel('wtware_configs', [
            'name', 'version', 'server_ip', 'server_port', 'screen_width',
            'screen_height', 'auto_start', 'network_drive', 'printer_config',
            'startup_script', 'shutdown_script', 'status', 'notes'
        ])
        filename = f'wtware_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'

        logger.info("Экспорт WTware завершен успешно: %s", filename)
        return send_file(
            excel_file,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        logger.error("Ошибка при экспорте WTware: %s", str(e), exc_info=True)
        flash(f'Ошибка при экспорте данных: {str(e)}', 'error')
        return redirect(url_for('wtware.wtware_list'))


@bluprint_wtware_routes.route('/import/wtware', methods=['GET', 'POST'])
def import_wtware():
    """Импорт конфигураций WTware из Excel"""
    if request.method == 'POST':
        logger.info("Запуск wtware_import, метод=POST")
        if 'excel_file' not in request.files:
            logger.warning("Файл не выбран при импорте WTware")
            flash('Файл не выбран', 'error')
            return redirect(request.url)

        file = request.files['excel_file']
        if file.filename == '':
            logger.warning("Пустое имя файла при импорте WTware")
            flash('Файл не выбран', 'error')
            return redirect(request.url)

        if not file.filename.endswith(('.xlsx', '.xls')):
            logger.warning("Неверное расширение файла при импорте WTware: %s", file.filename)
            flash('Поддерживаются только файлы Excel (.xlsx, .xls)', 'error')
            return redirect(request.url)

        try:
            logger.info("Импорт WTware из файла: %s", file.filename)
            success, message = import_from_excel(file, 'wtware_configs')

            if success:
                logger.info("Импорт WTware завершен успешно: %s", message)
                flash(message, 'success')
            else:
                logger.warning("Ошибка импорта WTware: %s", message)
                flash(message, 'error')

            return redirect(url_for('wtware.wtware_list'))

        except Exception as e:
            logger.error("Ошибка при импорте WTware: %s", str(e), exc_info=True)
            flash(f'Ошибка при импорте данных: {str(e)}', 'error')
            return redirect(request.url)

    logger.debug("Рендер формы импорта WTware")
    return render_template('wtware/import_wtware.html')


# ========== МАРШРУТЫ ДЛЯ УДАЛЕННОГО УПРАВЛЕНИЯ WTWARE ==========

@bluprint_wtware_routes.route('/wtware_connect/<int:config_id>', methods=['GET', 'POST'])
def wtware_connect(config_id):
    """Подключение к устройству WTware"""
    logger.info("Запуск wtware_connect, config_id=%s, метод=%s", config_id, request.method)
    db = get_db()

    try:
        config = db.query(WtwareConfig).filter(WtwareConfig.id == config_id).first()
        if not config:
            logger.warning("Конфигурация не найдена: config_id=%s", config_id)
            flash('Конфигурация не найдена', 'error')
            return redirect(url_for('wtware.wtware_list'))

        connection_status = None
        system_info = {}

        if request.method == 'POST':
            device_ip = request.form.get('device_ip')
            port = request.form.get('port', '80')
            logger.debug("Запрос подключения к WTware: device_ip=%s, port=%s", device_ip, port)

            if not device_ip:
                flash('IP адрес устройства обязателен', 'error')
            else:
                try:
                    port_int = int(port)
                    success, message, info = test_wtware_connection(device_ip, port_int)
                    connection_status = {
                        'success': success,
                        'message': message
                    }
                    system_info = info

                    if success:
                        logger.info("Успешное подключение к WTware: %s:%s", device_ip, port)
                        flash('Успешное подключение к устройству WTware!', 'success')
                    else:
                        logger.warning("Ошибка подключения к WTware %s:%s: %s", device_ip, port, message)
                        flash(f'Ошибка подключения: {message}', 'error')

                except ValueError:
                    logger.warning("Неверное значение порта: %s", port)
                    flash('Порт должен быть числом', 'error')
                except Exception as e:
                    logger.error("Ошибка при подключении к WTware: %s", str(e), exc_info=True)
                    flash(f'Ошибка подключения: {str(e)}', 'error')

        logger.info("Рендер страницы подключения к WTware: config_id=%s", config_id)
        return render_template('wtware/wtware_connect.html',
                              wtware_config=config,
                              connection_status=connection_status,
                              system_info=system_info)

    except Exception as e:
        logger.error("Ошибка в wtware_connect для config_id=%s: %s", config_id, str(e), exc_info=True)
        flash(f'Ошибка при загрузке страницы подключения: {str(e)}', 'error')
        return redirect(url_for('wtware.wtware_list'))


@bluprint_wtware_routes.route('/wtware_deploy_config/<int:config_id>', methods=['POST'])
def wtware_deploy_config(config_id):
    """Развертывание конфигурации на устройстве WTware"""
    logger.info("Запуск wtware_deploy_config, config_id=%s", config_id)
    db = get_db()

    try:
        config = db.query(WtwareConfig).filter(WtwareConfig.id == config_id).first()
        if not config:
            logger.warning("Конфигурация не найдена: config_id=%s", config_id)
            flash('Конфигурация не найдена', 'error')
            return redirect(url_for('wtware.wtware_connect', config_id=config_id))

        device_ip = request.form.get('device_ip')
        port = request.form.get('port', '80')
        logger.debug("Развертывание конфигурации: config_id=%s, device_ip=%s, port=%s",
                      config_id, device_ip, port)

        if not device_ip:
            flash('IP адрес устройства обязателен', 'error')
            return redirect(url_for('wtware.wtware_connect', config_id=config_id))

        port_int = int(port)
        config_dict = {
            'id': config.id,
            'name': config.name,
            'version': config.version,
            'server_ip': config.server_ip,
            'server_port': config.server_port,
            'screen_width': config.screen_width,
            'screen_height': config.screen_height,
            'auto_start': config.auto_start,
            'network_drive': config.network_drive,
            'printer_config': config.printer_config,
            'startup_script': config.startup_script,
            'shutdown_script': config.shutdown_script,
            'custom_config': config.custom_config,
            'status': config.status,
            'notes': config.notes,
        }
        config_content = generate_wtware_config(config_dict)

        success, message = upload_config_to_wtware(device_ip, config_content, port_int)

        if success:
            logger.info("Конфигурация развернута успешно: config_id=%s, device_ip=%s",
                         config_id, device_ip)
            flash(f'Конфигурация успешно развернута на устройстве {device_ip}!', 'success')

            deployment = WtwareDeployment(
                config_id=config_id,
                device_ip=device_ip,
                status='success',
            )
            db.add(deployment)
            db.commit()
        else:
            logger.warning("Ошибка развертывания конфигурации: config_id=%s, device_ip=%s, error=%s",
                           config_id, device_ip, message)
            flash(f'Ошибка развертывания: {message}', 'error')

            deployment = WtwareDeployment(
                config_id=config_id,
                device_ip=device_ip,
                status='error',
                error_message=message,
            )
            db.add(deployment)
            db.commit()

    except ValueError:
        logger.warning("Неверное значение порта при развертывании: %s", request.form.get('port', ''))
        flash('Порт должен быть числом', 'error')
    except Exception as e:
        db.rollback()
        logger.error("Ошибка при развертывании конфигурации config_id=%s: %s",
                      config_id, str(e), exc_info=True)
        flash(f'Ошибка при развертывании: {str(e)}', 'error')

    return redirect(url_for('wtware.wtware_connect', config_id=config_id))


@bluprint_wtware_routes.route('/wtware_restart_service/<int:config_id>', methods=['POST'])
def wtware_restart_service(config_id):
    """Перезапуск устройства WTware"""
    logger.info("Запуск wtware_restart_service, config_id=%s", config_id)
    db = get_db()

    try:
        config = db.query(WtwareConfig).filter(WtwareConfig.id == config_id).first()
        if not config:
            logger.warning("Конфигурация не найдена: config_id=%s", config_id)
            flash('Конфигурация не найдена', 'error')
            return redirect(url_for('wtware.wtware_list'))

        device_ip = request.form.get('device_ip')
        port = request.form.get('port', '80')
        logger.debug("Перезапуск WTware: config_id=%s, device_ip=%s, port=%s",
                      config_id, device_ip, port)

        if not device_ip:
            flash('IP адрес устройства обязателен', 'error')
            return redirect(url_for('wtware.wtware_connect', config_id=config_id))

        port_int = int(port)
        client = WTwareClient()

        if not client.connect(device_ip, port_int):
            logger.warning("Не удалось подключиться к устройству WTware: %s:%s", device_ip, port)
            flash('Не удалось подключиться к устройству', 'error')
            return redirect(url_for('wtware.wtware_connect', config_id=config_id))

        try:
            success, message = client.reboot_device()

            if success:
                logger.info("Устройство WTware перезапускается: %s", device_ip)
                flash(f'Устройство WTware {device_ip} перезапускается!', 'success')
            else:
                logger.warning("Ошибка перезапуска WTware %s: %s", device_ip, message)
                flash(f'Ошибка перезапуска: {message}', 'error')
        finally:
            client.disconnect()

    except ValueError:
        logger.warning("Неверное значение порта при перезапуске: %s", request.form.get('port', ''))
        flash('Порт должен быть числом', 'error')
    except Exception as e:
        logger.error("Ошибка при перезапуске WTware config_id=%s: %s", config_id, str(e), exc_info=True)
        flash(f'Ошибка при перезапуске: {str(e)}', 'error')

    return redirect(url_for('wtware.wtware_connect', config_id=config_id))


@bluprint_wtware_routes.route('/wtware_get_current_config/<int:config_id>', methods=['POST'])
def wtware_get_current_config(config_id):
    """Получение текущей конфигурации с устройства"""
    logger.info("Запуск wtware_get_current_config, config_id=%s", config_id)
    db = get_db()

    try:
        config = db.query(WtwareConfig).filter(WtwareConfig.id == config_id).first()
        if not config:
            logger.warning("Конфигурация не найдена: config_id=%s", config_id)
            flash('Конфигурация не найдена', 'error')
            return redirect(url_for('wtware.wtware_list'))

        device_ip = request.form.get('device_ip')
        username = request.form.get('username', 'root')
        password = request.form.get('password')
        port = request.form.get('port', 22)
        logger.debug("Получение конфигурации с устройства: config_id=%s, device_ip=%s, port=%s",
                      config_id, device_ip, port)

        if not device_ip or not password:
            flash('IP адрес устройства и пароль обязательны', 'error')
            return redirect(url_for('wtware.wtware_connect', config_id=config_id))

        client = WTwareSSHClient()

        if not client.connect(device_ip, username, password, port):
            logger.warning("Не удалось подключиться по SSH к устройству: %s:%s", device_ip, port)
            flash('Не удалось подключиться к устройству', 'error')
            return redirect(url_for('wtware.wtware_connect', config_id=config_id))

        try:
            success, current_config = client.download_config()

            if success:
                logger.info("Конфигурация получена с устройства: %s", device_ip)
                return render_template('wtware/wtware_current_config.html',
                                      wtware_config=config,
                                      current_config=current_config,
                                      device_ip=device_ip)
            else:
                logger.warning("Ошибка получения конфигурации с устройства %s: %s",
                               device_ip, current_config)
                flash(f'Ошибка получения конфигурации: {current_config}', 'error')

        except Exception as e:
            logger.error("Ошибка при работе с SSH клиентом: %s", str(e), exc_info=True)
            flash(f'Ошибка при получении конфигурации: {str(e)}', 'error')
        finally:
            client.disconnect()

    except Exception as e:
        logger.error("Ошибка в wtware_get_current_config config_id=%s: %s", config_id, str(e), exc_info=True)
        flash(f'Ошибка при получении конфигурации: {str(e)}', 'error')

    return redirect(url_for('wtware.wtware_connect', config_id=config_id))


# ========== СКАЧИВАНИЕ КОНФИГУРАЦИИ ==========

@bluprint_wtware_routes.route('/download_wtware_config/<int:config_id>')
def download_wtware_config(config_id):
    """Скачивание конфигурационного файла WTware"""
    logger.info("Запуск download_wtware_config, config_id=%s", config_id)
    db = get_db()

    try:
        config = db.query(WtwareConfig).filter(WtwareConfig.id == config_id).first()
        if not config:
            logger.warning("Конфигурация не найдена: config_id=%s", config_id)
            flash('Конфигурация не найдена', 'error')
            return redirect(url_for('wtware.wtware_list'))

        config_dict = {
            'id': config.id,
            'name': config.name,
            'version': config.version,
            'server_ip': config.server_ip,
            'server_port': config.server_port,
            'screen_width': config.screen_width,
            'screen_height': config.screen_height,
            'auto_start': config.auto_start,
            'network_drive': config.network_drive,
            'printer_config': config.printer_config,
            'startup_script': config.startup_script,
            'shutdown_script': config.shutdown_script,
            'custom_config': config.custom_config,
            'status': config.status,
            'notes': config.notes,
        }
        config_content = generate_wtware_config(config_dict)

        filename = f'wtware_config_{config.name}.conf'
        logger.info("Скачивание конфигурации WTware: config_id=%s, filename=%s",
                     config_id, filename)

        return Response(
            config_content,
            mimetype="text/plain",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )

    except Exception as e:
        logger.error("Ошибка при скачивании конфигурации WTware config_id=%s: %s",
                      config_id, str(e), exc_info=True)
        flash(f'Ошибка при скачивании: {str(e)}', 'error')
        return redirect(url_for('wtware.wtware_list'))


@bluprint_wtware_routes.route('/wtware_deployments')
def wtware_deployments():
    """История развертываний конфигураций"""
    logger.info("Запуск wtware_deployments")
    db = get_db()

    try:
        query = db.query(
            WtwareDeployment,
            WtwareConfig.name.label('config_name')
        ).join(
            WtwareConfig, WtwareDeployment.config_id == WtwareConfig.id
        ).order_by(WtwareDeployment.deployed_at.desc()).limit(50)

        deployments = query.all()
        logger.info("Найдено записей о развертываниях: %d", len(deployments))
        return render_template('wtware/wtware_deployments.html', deployments=deployments)

    except Exception as e:
        logger.error("Ошибка в wtware_deployments: %s", str(e), exc_info=True)
        flash(f'Ошибка при загрузке истории развертываний: {str(e)}', 'error')
        return render_template('wtware/wtware_deployments.html', deployments=[])


@bluprint_wtware_routes.route('/scripts')
def scripts_list():
    """Список всех скриптов"""
    logger.info("Запуск scripts_list")
    db = get_db()

    try:
        query = db.query(
            Script,
            func.count(ScriptResult.id).label('execution_count'),
            func.max(ScriptResult.executed_at).label('last_executed')
        ).outerjoin(
            ScriptResult, Script.id == ScriptResult.script_id
        ).group_by(Script.id).order_by(Script.created_at.desc())

        scripts = query.all()
        logger.info("Найдено скриптов: %d", len(scripts))
        return render_template('scripts/scripts_list.html', scripts=scripts)

    except Exception as e:
        logger.error("Ошибка в scripts_list: %s", str(e), exc_info=True)
        flash(f'Ошибка при загрузке списка скриптов: {str(e)}', 'error')
        return render_template('scripts/scripts_list.html', scripts=[])


# ========== УТИЛИТЫ ДЛЯ СКРИПТОВ ==========

def execute_script(script_content, script_type='bat'):
    """
    Выполняет скрипт и возвращает результат
    """
    logger.debug("Выполнение скрипта типа=%s, длина=%d символов",
                 script_type, len(script_content))
    try:
        with tempfile.NamedTemporaryFile(mode='w',
                                       suffix=f'.{script_type}',
                                       delete=False,
                                       encoding='utf-8') as temp_file:
            temp_file.write(script_content)
            temp_file.flush()
            temp_path = temp_file.name

        start_time = time.time()

        if script_type == 'bat':
            result = subprocess.run(
                ['cmd', '/c', temp_path],
                capture_output=True,
                text=True,
                timeout=300,
                encoding='cp866'
            )
        elif script_type == 'ps1':
            result = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-File', temp_path],
                capture_output=True,
                text=True,
                timeout=300,
                encoding='cp866'
            )
        else:
            raise ValueError(f"Unsupported script type: {script_type}")

        execution_time = time.time() - start_time

        try:
            os.unlink(temp_path)
        except Exception:
            pass

        success = result.returncode == 0

        if success:
            logger.info("Скрипт выполнен успешно, тип=%s, время=%.2fs", script_type, execution_time)
        else:
            logger.warning("Скрипт выполнен с ошибкой, тип=%s, код=%d, время=%.2fs",
                           script_type, result.returncode, execution_time)

        return {
            'success': success,
            'output': result.stdout,
            'error': result.stderr,
            'return_code': result.returncode,
            'execution_time': execution_time
        }

    except subprocess.TimeoutExpired:
        logger.error("Таймаут выполнения скрипта, тип=%s", script_type)
        return {
            'success': False,
            'output': '',
            'error': 'Script execution timeout (5 minutes)',
            'return_code': -1,
            'execution_time': 300
        }
    except Exception as e:
        logger.error("Ошибка при выполнении скрипта, тип=%s: %s", script_type, str(e), exc_info=True)
        return {
            'success': False,
            'output': '',
            'error': str(e),
            'return_code': -1,
            'execution_time': 0
        }


def save_script_result(db, script_id, result):
    """
    Сохраняет результат выполнения скрипта в базу данных
    """
    logger.debug("Сохранение результата выполнения скрипта: script_id=%s, success=%s",
                 script_id, result.get('success'))
    try:
        db.execute(text('''
            INSERT INTO script_results 
            (script_id, output, success, error_message, execution_time)
            VALUES (?, ?, ?, ?, ?)
        '''), (
            script_id,
            result['output'],
            result['success'],
            result['error'],
            result['execution_time']
        ))
        db.commit()
        logger.info("Результат выполнения скрипта сохранен: script_id=%s", script_id)
    except Exception as e:
        db.rollback()
        logger.error("Ошибка при сохранении результата выполнения скрипта script_id=%s: %s",
                      script_id, str(e), exc_info=True)


def get_script_results(db, script_id, limit=10):
    """
    Получает историю выполнения скрипта
    """
    logger.debug("Получение истории выполнения скрипта: script_id=%s, limit=%s",
                 script_id, limit)
    return db.execute(text('''
        SELECT * FROM script_results 
        WHERE script_id = ? 
        ORDER BY executed_at DESC 
        LIMIT ?
    '''), (script_id, limit)).fetchall()
