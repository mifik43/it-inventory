from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database_helper import db
from templates.base.requirements import permissions_required, permissions_required_all, permissions_required
from templates.roles.permissions import Permissions
from sqlalchemy import case
from models import Organization, Todo
from logger import logger

bluprint_organizations_routes = Blueprint("organizations", __name__)



@bluprint_organizations_routes.route('/organizations')
@permissions_required([Permissions.organizations_read])
def organizations():
    logger.info('Открыт список организаций')
    order_type = case(
        (Organization.type == 'ООО', 1),
        (Organization.type == 'ИП', 2),
        (Organization.type == 'Самозанятый', 3),
        else_=4
    )
    organizations_list = Organization.query.order_by(order_type, Organization.name).all()
    logger.debug(f'Загружено организаций: {len(organizations_list)}')
    return render_template('organizations/organizations.html', organizations=organizations_list)

@bluprint_organizations_routes.route('/add_organization', methods=['GET', 'POST'])
@permissions_required([Permissions.organizations_manage])
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
            logger.warning('Попытка добавить организацию без названия')
            flash('Название организации обязательно для заполнения', 'error')
            return render_template('add_organization.html')
        
        try:
            logger.info(f'Добавление организации: {name}')
            organization = Organization(
                name=name,
                type=org_type,
                inn=inn,
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address,
                notes=notes
            )
            db.session.add(organization)
            db.session.commit()
            logger.info(f'Организация добавлена: id={organization.id} name={organization.name}')
            flash('Организация успешно добавлена!', 'success')
            return redirect(url_for('organizations.organizations'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Ошибка при добавлении организации: {e}', exc_info=True)
            flash(f'Ошибка при добавлении организации: {str(e)}', 'error')
    
    return render_template('organizations/add_organization.html')

@bluprint_organizations_routes.route('/edit_organization/<int:org_id>', methods=['GET', 'POST'])
@permissions_required([Permissions.organizations_manage])
def edit_organization(org_id):
    organization = Organization.query.get(org_id)
    if not organization:
        logger.warning(f'Организация не найдена для редактирования: id={org_id}')
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
            logger.warning(f'Попытка обновить организацию без названия: id={org_id}')
            flash('Название организации обязательно для заполнения', 'error')
            return render_template('organizations/edit_organization.html', org=organization)
        
        try:
            logger.info(f'Обновление организации id={org_id}')
            organization.name = name
            organization.type = org_type
            organization.inn = inn
            organization.contact_person = contact_person
            organization.phone = phone
            organization.email = email
            organization.address = address
            organization.notes = notes
            db.session.commit()
            logger.info(f'Организация обновлена: id={org_id} name={organization.name}')
            flash('Данные организации успешно обновлены!', 'success')
            return redirect(url_for('organizations.organizations'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Ошибка при обновлении организации id={org_id}: {e}', exc_info=True)
            flash(f'Ошибка при обновлении организации: {str(e)}', 'error')
    
    return render_template('organizations/edit_organization.html', org=organization)

@bluprint_organizations_routes.route('/delete_organization/<int:org_id>')
@permissions_required([Permissions.organizations_manage])
def delete_organization(org_id):
    tasks_count = Todo.query.filter_by(organization_id=org_id).count()
    
    if tasks_count > 0:
        logger.warning(f'Попытка удалить организацию, используемую в задачах: id={org_id}')
        flash('Невозможно удалить организацию, так как она используется в задачах', 'error')
        return redirect(url_for('organizations.organizations'))
    
    organization = Organization.query.get(org_id)
    if not organization:
        logger.warning(f'Организация не найдена для удаления: id={org_id}')
        flash('Организация не найдена', 'error')
        return redirect(url_for('organizations.organizations'))
    
    try:
        logger.info(f'Удаление организации id={org_id} name={organization.name}')
        db.session.delete(organization)
        db.session.commit()
        flash('Организация успешно удалена!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Ошибка при удалении организации id={org_id}: {e}', exc_info=True)
        flash(f'Ошибка при удалении организации: {str(e)}', 'error')
    
    return redirect(url_for('organizations.organizations'))
