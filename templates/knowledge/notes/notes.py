from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database import get_db
from templates.base.requirements import permission_required, permissions_required_all, permissions_required_any
from templates.roles.permissions import Permissions

from datetime import datetime

bluprint_notes_routes = Blueprint("notes", __name__)


@bluprint_notes_routes.route('/notes')
@permission_required(Permissions.notes_read)
def notes_list():
    db = get_db()
    notes = db.execute('''
        SELECT n.*, u.username as author_name 
        FROM notes n 
        JOIN users u ON n.author_id = u.id 
        WHERE n.author_id = ?
        ORDER BY n.is_pinned DESC, n.updated_at DESC
    ''', (session['user_id'],)).fetchall()
    
    # Статистика для сегодня
    today = datetime.now().strftime('%Y-%m-%d')
    today_created = db.execute('''
        SELECT COUNT(*) as count FROM notes 
        WHERE DATE(created_at) = ? AND author_id = ?
    ''', (today, session['user_id'])).fetchone()['count']
    
    return render_template('knowledge/notes/notes.html', notes=notes, today_created=today_created)

@bluprint_notes_routes.route('/add_note', methods=['GET', 'POST'])
@permission_required(Permissions.notes_manage)
def add_note():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        color = request.form.get('color', '#ffffff')
        is_pinned = request.form.get('is_pinned') == '1'
        
        if not title or not content:
            flash('Заголовок и содержание обязательны для заполнения', 'error')
            return render_template('knowledge/notes/add_note.html')
        
        db = get_db()
        try:
            db.execute('''
                INSERT INTO notes (title, content, color, is_pinned, author_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, content, color, is_pinned, session['user_id']))
            db.commit()
            flash('Заметка успешно создана!', 'success')
            return redirect(url_for('notes.notes_list'))
        except Exception as e:
            flash(f'Ошибка при создании заметки: {str(e)}', 'error')
    
    return render_template('knowledge/notes/add_note.html')

# ========== МАРШРУТЫ ДЛЯ УДАЛЕНИЯ И РЕДАКТИРОВАНИЯ СТАТЕЙ И ЗАМЕТОК ==========


@bluprint_notes_routes.route('/delete_note/<int:note_id>')
@permission_required(Permissions.notes_manage)
def delete_note(note_id):
    db = get_db()
    note = db.execute('SELECT * FROM notes WHERE id = ? AND author_id = ?', 
                     (note_id, session['user_id'])).fetchone()
    
    if not note:
        flash('Заметка не найдена', 'error')
        return redirect(url_for('notes.notes_list'))
    
    try:
        db.execute('DELETE FROM notes WHERE id = ?', (note_id,))
        db.commit()
        flash('Заметка успешно удалена!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении заметки: {str(e)}', 'error')
    
    return redirect(url_for('notes.notes_list'))

@bluprint_notes_routes.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
@permission_required(Permissions.notes_manage)
def edit_note(note_id):
    db = get_db()
    note = db.execute('SELECT * FROM notes WHERE id = ? AND author_id = ?', 
                     (note_id, session['user_id'])).fetchone()
    
    if not note:
        flash('Заметка не найдена', 'error')
        return redirect(url_for('notes.notes_list'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        color = request.form.get('color', '#ffffff')
        is_pinned = request.form.get('is_pinned') == '1'
        
        if not title or not content:
            flash('Заголовок и содержание обязательны для заполнения', 'error')
            return render_template('knowledge/notes/edit_note.html', note=note)
        
        try:
            db.execute('''
                UPDATE notes SET 
                title=?, content=?, color=?, is_pinned=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (title, content, color, is_pinned, note_id))
            db.commit()
            flash('Заметка успешно обновлена!', 'success')
            return redirect(url_for('notes.notes_list'))
        except Exception as e:
            flash(f'Ошибка при обновлении заметки: {str(e)}', 'error')
    
    return render_template('knowledge/notes/edit_note.html', note=note)

@bluprint_notes_routes.route('/toggle_pin_note/<int:note_id>')
@permission_required(Permissions.notes_manage)
def toggle_pin_note(note_id):
    db = get_db()
    note = db.execute('SELECT * FROM notes WHERE id = ? AND author_id = ?', 
                     (note_id, session['user_id'])).fetchone()
    
    if not note:
        flash('Заметка не найдена', 'error')
        return redirect(url_for('notes.notes_list'))
    
    try:
        db.execute('UPDATE notes SET is_pinned = NOT is_pinned WHERE id = ?', (note_id,))
        db.commit()
        flash('Статус закрепления изменен!', 'success')
    except Exception as e:
        flash(f'Ошибка при изменении статуса: {str(e)}', 'error')
    
    return redirect(url_for('notes.notes_list'))