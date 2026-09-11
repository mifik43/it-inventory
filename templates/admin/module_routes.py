from flask import Blueprint, render_template, request, redirect, url_for, flash
from templates.base.database_helper import db
from templates.base.requirements import permissions_required
from templates.roles.permissions import Permissions
from templates.base.module_registry import (
    MODULES, get_all_module_settings, ensure_module_settings
)
from models import ModuleSettings

bluprint_admin_modules = Blueprint('admin_modules', __name__, url_prefix='/admin/modules')


@bluprint_admin_modules.route('/')
@permissions_required([Permissions.roles_manage])   # только админы
def modules_list():
    ensure_module_settings()
    modules = get_all_module_settings()
    return render_template('admin/modules.html', modules=modules)


@bluprint_admin_modules.route('/toggle/<module_key>', methods=['POST'])
@permissions_required([Permissions.roles_manage])
def toggle_module(module_key):
    setting = ModuleSettings.query.filter_by(module_key=module_key).first()
    if not setting:
        flash(f'Модуль «{module_key}» не найден', 'error')
        return redirect(url_for('admin_modules.modules_list'))

    setting.is_enabled = not setting.is_enabled
    db.session.commit()

    status = 'включён' if setting.is_enabled else 'отключён'
    flash(f'Модуль «{setting.display_name}» {status}', 'success')
    return redirect(url_for('admin_modules.modules_list'))