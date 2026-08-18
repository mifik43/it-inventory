from flask import render_template, request, redirect, url_for, flash, Blueprint
from sqlalchemy import or_

from templates.base.database_helper import db
from templates.base.requirements import permissions_required
from templates.roles.permissions import Permissions
from models import SoftwareCube
from logger import logger

bluprint_cubes_routes = Blueprint("cubes", __name__)

def get_cubes():
    logger.debug('Запрос списка кубиков')
    return SoftwareCube.query.order_by(SoftwareCube.created_at.desc()).all()

@bluprint_cubes_routes.route('/cubes')
@permissions_required([Permissions.cubes_read])
def cubes():
    logger.info('Открыт список кубиков')
    cubes_list = get_cubes()
    return render_template('cubes/cubes.html', cubes=cubes_list)

@bluprint_cubes_routes.route('/add_cube', methods=['GET', 'POST'])
@permissions_required([Permissions.cubes_manage])
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
        
        try:
            logger.info(f'Добавление нового кубика name: {name}, software_type: {software_type}')
            cube = SoftwareCube(
                name=name,
                software_type=software_type,
                license_type=license_type,
                license_key=license_key,
                contract_number=contract_number,
                contract_date=contract_date,
                price=price,
                users_count=users_count,
                support_contact=support_contact,
                phone=phone,
                email=email,
                object_location=object_location,
                city=city,
                status=status,
                renewal_date=renewal_date,
                notes=notes
            )
            db.session.add(cube)
            db.session.commit()
            flash('Кубик успешно добавлен!', 'success')
            logger.info(f'Кубик добавлен: id={cube.id} name={cube.name}')
            return redirect(url_for('cubes.cubes'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Ошибка при добавлении кубика: {e}', exc_info=True)
            flash(f'Ошибка при добавлении кубика: {str(e)}', 'error')
    
    return render_template('cubes/add_cube.html')

@bluprint_cubes_routes.route('/edit_cube/<int:cube_id>', methods=['GET', 'POST'])
@permissions_required([Permissions.cubes_manage])
def edit_cube(cube_id):
    
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
            cube = SoftwareCube.query.get_or_404(cube_id)
            logger.info(f'Обновление кубика id={cube_id} name: {cube.name}')
            cube.name = name
            cube.software_type = software_type
            cube.license_type = license_type
            cube.license_key = license_key
            cube.contract_number = contract_number
            cube.contract_date = contract_date
            cube.price = price
            cube.users_count = users_count
            cube.support_contact = support_contact
            cube.phone = phone
            cube.email = email
            cube.object_location = object_location
            cube.city = city
            cube.status = status
            cube.renewal_date = renewal_date
            cube.notes = notes
            db.session.commit()
            flash('Данные кубика успешно обновлены!', 'success')
            logger.info(f'Кубик обновлен: id={cube.id} name={cube.name}')
            return redirect(url_for('cubes.cubes'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Ошибка при обновлении кубика id={cube_id}: {e}', exc_info=True)
            flash(f'Ошибка при обновлении кубика: {str(e)}', 'error')
    
    cube = SoftwareCube.query.get_or_404(cube_id)
    return render_template('cubes/edit_cube.html', cube=cube)

@bluprint_cubes_routes.route('/delete_cube/<int:cube_id>')
@permissions_required([Permissions.cubes_manage])
def delete_cube(cube_id):
    try:
        logger.info(f'Удаление кубика id={cube_id}')
        cube = SoftwareCube.query.get_or_404(cube_id)
        db.session.delete(cube)
        db.session.commit()
        flash('Кубик успешно удален!', 'success')
        logger.info(f'Кубик удалён: id={cube_id} name={cube.name}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Ошибка при удалении кубика id={cube_id}: {e}', exc_info=True)
        flash(f'Ошибка при удалении кубика: {str(e)}', 'error')
    
    return redirect(url_for('cubes.cubes'))

@bluprint_cubes_routes.route('/cube_search')
@permissions_required([Permissions.cubes_read])
def cube_search():
    query = request.args.get('q', '')
    logger.info(f'Поиск кубиков: query="{query}"')
    search_pattern = f'%{query}%'
    cubes_list = SoftwareCube.query.filter(
        or_(
            SoftwareCube.name.ilike(search_pattern),
            SoftwareCube.license_key.ilike(search_pattern),
            SoftwareCube.contract_number.ilike(search_pattern),
            SoftwareCube.object_location.ilike(search_pattern),
            SoftwareCube.support_contact.ilike(search_pattern)
        )
    ).order_by(SoftwareCube.created_at.desc()).all()
    logger.debug(f'Найдено кубиков: {len(cubes_list)}')
    return render_template('cubes/cubes.html', cubes=cubes_list, search_query=query)
