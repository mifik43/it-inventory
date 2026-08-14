from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from templates.base.database_helper import db
from templates.base.requirements import permissions_required
from templates.roles.permissions import Permissions
from models import Note, User
from datetime import datetime

bluprint_notes_routes = Blueprint("notes", __name__)


@bluprint_notes_routes.route('/notes')
@permissions_required(Permissions.notes_read)
def notes_list():
    # Получаем заметки текущего пользователя, сортируем по закреплению и обновлению
    notes = Note.query.filter_by(author_id=session['user_id'])\
        .order_by(Note.is_pinned.desc(), Note.updated_at.desc())\
        .all()

    # Статистика: количество заметок, созданных сегодня
    today = datetime.now().date()
    today_created = Note.query.filter(
        db.func.date(Note.created_at) == today,
        Note.author_id == session['user_id']
    ).count()

    return render_template('knowledge/notes/notes.html', notes=notes, today_created=today_created)


@bluprint_notes_routes.route('/add_note', methods=['GET', 'POST'])
@permissions_required(Permissions.notes_manage)
def add_note():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        color = request.form.get('color', '#ffffff')
        is_pinned = request.form.get('is_pinned') == '1'

        if not title or not content:
            flash('Заголовок и содержание обязательны для заполнения', 'error')
            return render_template('knowledge/notes/add_note.html')

        note = Note(
            title=title,
            content=content,
            color=color,
            is_pinned=is_pinned,
            author_id=session['user_id']
        )
        db.session.add(note)
        try:
            db.session.commit()
            flash('Заметка успешно создана!', 'success')
            return redirect(url_for('notes.notes_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании заметки: {str(e)}', 'error')

    return render_template('knowledge/notes/add_note.html')


@bluprint_notes_routes.route('/delete_note/<int:note_id>')
@permissions_required(Permissions.notes_manage)
def delete_note(note_id):
    note = Note.query.filter_by(id=note_id, author_id=session['user_id']).first()
    if not note:
        flash('Заметка не найдена', 'error')
        return redirect(url_for('notes.notes_list'))

    try:
        db.session.delete(note)
        db.session.commit()
        flash('Заметка успешно удалена!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении заметки: {str(e)}', 'error')

    return redirect(url_for('notes.notes_list'))


@bluprint_notes_routes.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
@permissions_required(Permissions.notes_manage)
def edit_note(note_id):
    note = Note.query.filter_by(id=note_id, author_id=session['user_id']).first()
    if not note:
        flash('Заметка не найдена', 'error')
        return redirect(url_for('notes.notes_list'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        color = request.form.get('color', '#ffffff')
        is_pinned = request.form.get('is_pinned') == '1'

        if not title or not content:
            flash('Заголовок и содержание обязательны для заполнения', 'error')
            return render_template('knowledge/notes/edit_note.html', note=note)

        # Обновляем поля
        note.title = title
        note.content = content
        note.color = color
        note.is_pinned = is_pinned
        note.updated_at = datetime.utcnow()

        try:
            db.session.commit()
            flash('Заметка успешно обновлена!', 'success')
            return redirect(url_for('notes.notes_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении заметки: {str(e)}', 'error')

    return render_template('knowledge/notes/edit_note.html', note=note)


@bluprint_notes_routes.route('/toggle_pin_note/<int:note_id>')
@permissions_required(Permissions.notes_manage)
def toggle_pin_note(note_id):
    note = Note.query.filter_by(id=note_id, author_id=session['user_id']).first()
    if not note:
        flash('Заметка не найдена', 'error')
        return redirect(url_for('notes.notes_list'))

    try:
        note.is_pinned = not note.is_pinned
        db.session.commit()
        flash('Статус закрепления изменен!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при изменении статуса: {str(e)}', 'error')

    return redirect(url_for('notes.notes_list'))