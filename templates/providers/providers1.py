from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database import get_db
from templates.base.requirements import permission_required, permissions_required_all, permissions_required_any
from templates.roles.permissions import Permissions
from templates.base.organization_utils import get_user_organizations_list, has_organization_access

bluprint_provider_routes = Blueprint("providers", __name__)

@bluprint_provider_routes.route('/providers')
@permission_required(Permissions.providers_read)
def providers():
    db = get_db()
    providers_list = db.execute('''
        SELECT * FROM providers 
        ORDER BY created_at DESC
    ''').fetchall()
    return render_template('providers/providers.html', providers=providers_list)

@bluprint_provider_routes.route('/add_provider', methods=['GET', 'POST'])
@permission_required(Permissions.providers_manage)
def add_provider():
    if request.method == 'POST':
        name = request.form['name']
        service_type = request.form['service_type']
        contract_number = request.form.get('contract_number', '')
        contract_date = request.form.get('contract_date', '')
        ip_range = request.form.get('ip_range', '')
        speed = request.form.get('speed', '')
        price = request.form.get('price', 0)
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        object_location = request.form['object_location']
        city = request.form['city']
        status = request.form['status']
        notes = request.form.get('notes', '')
        
        # Преобразуем цену в число
        try:
            price = float(price) if price else 0
        except ValueError:
            price = 0
        
        db = get_db()
        try:
            db.execute('''
                INSERT INTO providers 
                (name, service_type, contract_number, contract_date, ip_range, speed, price, 
                 contact_person, phone, email, object_location, city, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, service_type, contract_number, contract_date, ip_range, speed, price,
                contact_person, phone, email, object_location, city, status, notes
            ))
            db.commit()
            flash('Провайдер успешно добавлен!', 'success')
            return redirect(url_for('providers.providers'))
        except Exception as e:
            flash(f'Ошибка при добавлении провайдера: {str(e)}', 'error')
    
    return render_template('providers/add_provider.html')

@bluprint_provider_routes.route('/edit_provider/<int:provider_id>', methods=['GET', 'POST'])
@permission_required(Permissions.providers_manage)
def edit_provider(provider_id):
    db = get_db()
    
    if request.method == 'POST':
        name = request.form['name']
        service_type = request.form['service_type']
        contract_number = request.form.get('contract_number', '')
        contract_date = request.form.get('contract_date', '')
        ip_range = request.form.get('ip_range', '')
        speed = request.form.get('speed', '')
        price = request.form.get('price', 0)
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        object_location = request.form['object_location']
        city = request.form['city']
        status = request.form['status']
        notes = request.form.get('notes', '')
        
        # Преобразуем цену в число
        try:
            price = float(price) if price else 0
        except ValueError:
            price = 0
        
        try:
            db.execute('''
                UPDATE providers SET 
                name=?, service_type=?, contract_number=?, contract_date=?, ip_range=?, speed=?, price=?,
                contact_person=?, phone=?, email=?, object_location=?, city=?, status=?, notes=?
                WHERE id=?
            ''', (
                name, service_type, contract_number, contract_date, ip_range, speed, price,
                contact_person, phone, email, object_location, city, status, notes, provider_id
            ))
            db.commit()
            flash('Данные провайдера успешно обновлены!', 'success')
            return redirect(url_for('providers.providers'))
        except Exception as e:
            flash(f'Ошибка при обновлении провайдера: {str(e)}', 'error')
    
    provider = db.execute('SELECT * FROM providers WHERE id=?', (provider_id,)).fetchone()
    return render_template('providers/edit_provider.html', provider=provider)

@bluprint_provider_routes.route('/delete_provider/<int:provider_id>')
@permission_required(Permissions.providers_manage)
def delete_provider(provider_id):
    db = get_db()
    try:
        db.execute('DELETE FROM providers WHERE id=?', (provider_id,))
        db.commit()
        flash('Провайдер успешно удален!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении провайдера: {str(e)}', 'error')
    
    return redirect(url_for('providers.providers'))

@bluprint_provider_routes.route('/provider_search')
@permission_required(Permissions.providers_read)
def provider_search():
    query = request.args.get('q', '')
    db = get_db()
    
    providers_list = db.execute('''
        SELECT * FROM providers 
        WHERE name LIKE ? OR contract_number LIKE ? OR object_location LIKE ? OR city LIKE ? OR contact_person LIKE ?
        ORDER BY created_at DESC
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    
    return render_template('providers/providers.html', providers=providers_list, search_query=query)
