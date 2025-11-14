from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database import get_db
from templates.base.requirements import permission_required, permissions_required_all, permissions_required_any
from templates.roles.permissions import Permissions

bluprint_organizations_routes = Blueprint("organizations", __name__)



@bluprint_organizations_routes.route('/organizations')
@permission_required(Permissions.organizations_read)
def organizations():
    db = get_db()
    organizations_list = db.execute('''
        SELECT * FROM organizations 
        ORDER BY 
            CASE type
                WHEN 'ООО' THEN 1
                WHEN 'ИП' THEN 2
                WHEN 'Самозанятый' THEN 3
                ELSE 4
            END,
            name
    ''').fetchall()
    return render_template('organizations/organizations.html', organizations=organizations_list)

@bluprint_organizations_routes.route('/add_organization', methods=['GET', 'POST'])
@permission_required(Permissions.organizations_manage)
def add_organization():
    if request.method == 'POST':
        name = request.form['name']
        org_type = request.form['type']
        inn = request.form.get('inn', '')
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        notes = request.form.get('notes', '')
        
        # Валидация
        if not name:
            flash('Название организации обязательно для заполнения', 'error')
            return render_template('add_organization.html')
        
        db = get_db()
        try:
            db.execute('''
                INSERT INTO organizations (name, type, inn, contact_person, phone, email, address, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, org_type, inn, contact_person, phone, email, address, notes))
            db.commit()
            flash('Организация успешно добавлена!', 'success')
            return redirect(url_for('organizations.organizations'))
        except Exception as e:
            flash(f'Ошибка при добавлении организации: {str(e)}', 'error')
    
    return render_template('organizations/add_organization.html')

@bluprint_organizations_routes.route('/edit_organization/<int:org_id>', methods=['GET', 'POST'])
@permission_required(Permissions.organizations_manage)
def edit_organization(org_id):
    db = get_db()
    
    org = db.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone()
    if not org:
        flash('Организация не найдена', 'error')
        return redirect(url_for('organizations.organizations'))
    
    if request.method == 'POST':
        name = request.form['name']
        org_type = request.form['type']
        inn = request.form.get('inn', '')
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        notes = request.form.get('notes', '')
        
        # Валидация
        if not name:
            flash('Название организации обязательно для заполнения', 'error')
            return render_template('organizations/edit_organization.html', org=org)
        
        try:
            db.execute('''
                UPDATE organizations SET 
                name=?, type=?, inn=?, contact_person=?, phone=?, email=?, address=?, notes=?
                WHERE id=?
            ''', (name, org_type, inn, contact_person, phone, email, address, notes, org_id))
            db.commit()
            flash('Данные организации успешно обновлены!', 'success')
            return redirect(url_for('organizations.organizations'))
        except Exception as e:
            flash(f'Ошибка при обновлении организации: {str(e)}', 'error')
    
    return render_template('organizations/edit_organization.html', org=org)

@bluprint_organizations_routes.route('/delete_organization/<int:org_id>')
@permission_required(Permissions.organizations_manage)
def delete_organization(org_id):
    db = get_db()
    
    # Проверяем, используется ли организация в задачах
    tasks_count = db.execute('SELECT COUNT(*) as count FROM todos WHERE organization_id = ?', (org_id,)).fetchone()['count']
    
    if tasks_count > 0:
        flash('Невозможно удалить организацию, так как она используется в задачах', 'error')
        return redirect(url_for('organizations.organizations'))
    
    try:
        db.execute('DELETE FROM organizations WHERE id = ?', (org_id,))
        db.commit()
        flash('Организация успешно удалена!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении организации: {str(e)}', 'error')
    
    return redirect(url_for('organizations.organizations'))
