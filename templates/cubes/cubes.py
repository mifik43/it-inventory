from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database import get_db
from templates.base.requirements import permission_required, permissions_required_all, permissions_required_any
from templates.roles.permissions import Permissions

bluprint_cubes_routes = Blueprint("cubes", __name__)

def get_cubes():
    db = get_db()
    cubes_list = db.execute('''
        SELECT * FROM software_cubes 
        ORDER BY created_at DESC
    ''').fetchall()
    return cubes_list

@bluprint_cubes_routes.route('/cubes')
@permission_required(Permissions.cubes_read)
def cubes():
    cubes_list = get_cubes()
    return render_template('cubes/cubes.html', cubes=cubes_list)

@bluprint_cubes_routes.route('/add_cube', methods=['GET', 'POST'])
@permission_required(Permissions.cubes_manage)
def add_cube():
    if request.method == 'POST':
        name = request.form['name']
        software_type = request.form['software_type']
        license_type = request.form['license_type']
        license_key = request.form.get('license_key', '')
        contract_number = request.form.get('contract_number', '')
        contract_date = request.form.get('contract_date', '')
        price = request.form.get('price', 0)
        users_count = request.form.get('users_count', 1)
        support_contact = request.form.get('support_contact', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        object_location = request.form['object_location']
        city = request.form['city']
        status = request.form['status']
        renewal_date = request.form.get('renewal_date', '')
        notes = request.form.get('notes', '')
        
        # Преобразуем цены и количество в числа
        try:
            price = float(price) if price else 0
            users_count = int(users_count) if users_count else 1
        except ValueError:
            price = 0
            users_count = 1
        
        db = get_db()
        try:
            db.execute('''
                INSERT INTO software_cubes 
                (name, software_type, license_type, license_key, contract_number, contract_date, price, users_count, 
                 support_contact, phone, email, object_location, city, status, renewal_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, software_type, license_type, license_key, contract_number, contract_date, price, users_count,
                  support_contact, phone, email, object_location, city, status, renewal_date, notes))
            db.commit()
            flash('Кубик успешно добавлен!', 'success')
            return redirect(url_for('cubes.cubes'))
        except Exception as e:
            flash(f'Ошибка при добавлении кубика: {str(e)}', 'error')
    
    return render_template('cubes/add_cube.html')

@bluprint_cubes_routes.route('/edit_cube/<int:cube_id>', methods=['GET', 'POST'])
@permission_required(Permissions.cubes_manage)
def edit_cube(cube_id):
    db = get_db()
    
    if request.method == 'POST':
        name = request.form['name']
        software_type = request.form['software_type']
        license_type = request.form['license_type']
        license_key = request.form.get('license_key', '')
        contract_number = request.form.get('contract_number', '')
        contract_date = request.form.get('contract_date', '')
        price = request.form.get('price', 0)
        users_count = request.form.get('users_count', 1)
        support_contact = request.form.get('support_contact', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        object_location = request.form['object_location']
        city = request.form['city']
        status = request.form['status']
        renewal_date = request.form.get('renewal_date', '')
        notes = request.form.get('notes', '')
        
        # Преобразуем цены и количество в числа
        try:
            price = float(price) if price else 0
            users_count = int(users_count) if users_count else 1
        except ValueError:
            price = 0
            users_count = 1
        
        try:
            db.execute('''
                UPDATE software_cubes SET 
                name=?, software_type=?, license_type=?, license_key=?, contract_number=?, contract_date=?, price=?, users_count=?,
                support_contact=?, phone=?, email=?, object_location=?, city=?, status=?, renewal_date=?, notes=?
                WHERE id=?
            ''', (name, software_type, license_type, license_key, contract_number, contract_date, price, users_count,
                  support_contact, phone, email, object_location, city, status, renewal_date, notes, cube_id))
            db.commit()
            flash('Данные кубика успешно обновлены!', 'success')
            return redirect(url_for('cubes.cubes'))
        except Exception as e:
            flash(f'Ошибка при обновлении кубика: {str(e)}', 'error')
    
    cube = db.execute('SELECT * FROM software_cubes WHERE id=?', (cube_id,)).fetchone()
    return render_template('cubes/edit_cube.html', cube=cube)

@bluprint_cubes_routes.route('/delete_cube/<int:cube_id>')
@permission_required(Permissions.cubes_manage)
def delete_cube(cube_id):
    db = get_db()
    try:
        db.execute('DELETE FROM software_cubes WHERE id=?', (cube_id,))
        db.commit()
        flash('Кубик успешно удален!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении кубика: {str(e)}', 'error')
    
    return redirect(url_for('cubes.cubes'))

@bluprint_cubes_routes.route('/cube_search')
@permission_required(Permissions.cubes_read)
def cube_search():
    query = request.args.get('q', '')
    db = get_db()
    
    cubes_list = db.execute('''
        SELECT * FROM software_cubes 
        WHERE name LIKE ? OR license_key LIKE ? OR contract_number LIKE ? OR object_location LIKE ? OR support_contact LIKE ?
        ORDER BY created_at DESC
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    
    return render_template('cubes/cubes.html', cubes=cubes_list, search_query=query)
