from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from templates.base.requirements import login_required, get_current_user, permissions_required
from templates.roles.permissions import Permissions
from templates.base.database_helper import db
from models import PasswordFolder, PasswordEntry, PasswordAccess, PasswordHistory, Organization, User
from .crypto import encrypt_password, decrypt_password, generate_password
from sqlalchemy import desc

password_bp = Blueprint('password_manager', __name__, url_prefix='/passwords')

def user_can_view_entry(user_id, entry):
    if entry.created_by == user_id:
        return True
    access = PasswordAccess.query.filter_by(entry_id=entry.id, user_id=user_id).first()
    if access and access.can_view:
        return True
    if entry.folder and entry.folder.organization_id:
        user = User.query.get(user_id)
        if user and user.organization_id == entry.folder.organization_id:
            return True
    return False

def user_can_edit_entry(user_id, entry):
    if entry.created_by == user_id:
        return True
    access = PasswordAccess.query.filter_by(entry_id=entry.id, user_id=user_id).first()
    if access and access.can_edit:
        return True
    return False

@password_bp.route('/folders')
@login_required
@permissions_required([Permissions.password_manager_read])
def folders():
    user = get_current_user()
    organizations = Organization.query.order_by(Organization.name).all()  # добавьте эту строку
    if user.role == 'admin':
        folders = PasswordFolder.query.order_by(PasswordFolder.name).all()
    else:
        folders = PasswordFolder.query.filter(
            (PasswordFolder.organization_id == user.organization_id) |
            (PasswordFolder.organization_id.is_(None))
        ).order_by(PasswordFolder.name).all()
    return render_template('password_manager/folders.html', folders=folders, organizations=organizations)

@password_bp.route('/folder/<int:folder_id>')
@login_required
@permissions_required([Permissions.password_manager_read])
def folder_entries(folder_id):
    folder = PasswordFolder.query.get_or_404(folder_id)
    user = get_current_user()
    if folder.organization_id and user.organization_id != folder.organization_id and user.role != 'admin':
        flash('Нет доступа к этой папке', 'error')
        return redirect(url_for('password_manager.folders'))
    entries = PasswordEntry.query.filter_by(folder_id=folder_id).order_by(PasswordEntry.name).all()
    if user.role != 'admin':
        visible = []
        for e in entries:
            if user_can_view_entry(user.id, e):
                visible.append(e)
        entries = visible
    return render_template('password_manager/entries.html', folder=folder, entries=entries)

@password_bp.route('/folder/add', methods=['POST'])
@login_required
@permissions_required([Permissions.password_manager_manage])
def add_folder():
    name = request.form.get('name')
    org_id = request.form.get('organization_id')
    if not name:
        flash('Название обязательно', 'error')
        return redirect(url_for('password_manager.folders'))
    if org_id and org_id.isdigit():
        org_id = int(org_id)
    else:
        org_id = None
    folder = PasswordFolder(name=name, organization_id=org_id)
    db.session.add(folder)
    db.session.commit()
    flash('Папка создана', 'success')
    return redirect(url_for('password_manager.folders'))

@password_bp.route('/entry/add/<int:folder_id>', methods=['GET', 'POST'])
@login_required
@permissions_required([Permissions.password_manager_manage])
def add_entry(folder_id):
    folder = PasswordFolder.query.get_or_404(folder_id)
    user = get_current_user()
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        url = request.form.get('url')
        plain_password = request.form.get('password')
        notes = request.form.get('notes')
        if not name:
            flash('Название обязательно', 'error')
            return render_template('password_manager/entry_form.html', folder=folder, entry=None)
        if not plain_password:
            plain_password = generate_password(16, True, True, True)
        encrypted = encrypt_password(plain_password)
        entry = PasswordEntry(
            folder_id=folder_id,
            name=name,
            username=username,
            url=url,
            password_encrypted=encrypted,
            notes=notes,
            created_by=user.id
        )
        db.session.add(entry)
        db.session.commit()
        flash('Запись создана', 'success')
        return redirect(url_for('password_manager.folder_entries', folder_id=folder_id))
    return render_template('password_manager/entry_form.html', folder=folder, entry=None)

@password_bp.route('/entry/<int:entry_id>')
@login_required
@permissions_required([Permissions.password_manager_read])
def view_entry(entry_id):
    entry = PasswordEntry.query.get_or_404(entry_id)
    user = get_current_user()
    if not user_can_view_entry(user.id, entry):
        flash('Нет доступа к этой записи', 'error')
        return redirect(url_for('password_manager.folders'))
    decrypted = decrypt_password(entry.password_encrypted)
    return render_template('password_manager/entry_view.html', entry=entry, decrypted=decrypted)

@password_bp.route('/entry/<int:entry_id>/edit', methods=['GET', 'POST'])
@login_required
@permissions_required([Permissions.password_manager_manage])
def edit_entry(entry_id):
    entry = PasswordEntry.query.get_or_404(entry_id)
    user = get_current_user()
    if not user_can_edit_entry(user.id, entry):
        flash('Нет прав на редактирование', 'error')
        return redirect(url_for('password_manager.folders'))
    if request.method == 'POST':
        old_encrypted = entry.password_encrypted
        entry.name = request.form.get('name')
        entry.username = request.form.get('username')
        entry.url = request.form.get('url')
        new_plain = request.form.get('password')
        entry.notes = request.form.get('notes')
        if new_plain and new_plain != decrypt_password(old_encrypted):
            entry.password_encrypted = encrypt_password(new_plain)
            history = PasswordHistory(
                entry_id=entry.id,
                old_password_encrypted=old_encrypted,
                changed_by=user.id
            )
            db.session.add(history)
        db.session.commit()
        flash('Запись обновлена', 'success')
        return redirect(url_for('password_manager.view_entry', entry_id=entry_id))
    decrypted = decrypt_password(entry.password_encrypted)
    return render_template('password_manager/entry_form.html', folder=entry.folder, entry=entry, decrypted=decrypted)

@password_bp.route('/entry/<int:entry_id>/delete', methods=['POST'])
@login_required
@permissions_required([Permissions.password_manager_manage])
def delete_entry(entry_id):
    entry = PasswordEntry.query.get_or_404(entry_id)
    user = get_current_user()
    if user.role != 'admin' and entry.created_by != user.id:
        flash('Нет прав на удаление', 'error')
        return redirect(url_for('password_manager.folders'))
    folder_id = entry.folder_id
    db.session.delete(entry)
    db.session.commit()
    flash('Запись удалена', 'success')
    return redirect(url_for('password_manager.folder_entries', folder_id=folder_id))

@password_bp.route('/history/<int:entry_id>')
@login_required
@permissions_required([Permissions.password_manager_read])
def history(entry_id):
    entry = PasswordEntry.query.get_or_404(entry_id)
    user = get_current_user()
    if not user_can_view_entry(user.id, entry):
        flash('Нет доступа', 'error')
        return redirect(url_for('password_manager.folders'))
    history = PasswordHistory.query.filter_by(entry_id=entry_id).order_by(desc(PasswordHistory.changed_at)).all()
    history_data = []
    for h in history:
        decrypted_old = decrypt_password(h.old_password_encrypted)
        changer = User.query.get(h.changed_by)
        history_data.append({
            'old_password': decrypted_old,
            'changed_at': h.changed_at,
            'changer': changer.username if changer else 'Unknown'
        })
    return render_template('password_manager/history.html', entry=entry, history=history_data)