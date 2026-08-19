from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from sqlalchemy import func, distinct

from templates.base.database_helper import db
from templates.base.requirements import permissions_required
from templates.roles.permissions import Permissions
from models import Organization, User, Log

bluprint_organizations_routes = Blueprint("organizations", __name__)

# ========== ОСНОВНЫЕ МАРШРУТЫ ==========

@bluprint_organizations_routes.route('/organizations')
@permissions_required([Permissions.organizations_read])
def organizations():
    organizations_list = Organization.query.order_by(
        db.case(
            (Organization.type == 'ООО', 1),
            (Organization.type == 'ИП', 2),
            (Organization.type == 'Самозанятый', 3),
            else_=4
        ),
        Organization.name
    ).all()
    return render_template('organizations/organizations.html', organizations=organizations_list)

@bluprint_organizations_routes.route('/add_organization', methods=['GET', 'POST'])
@permissions_required([Permissions.organizations_manage])
def add_organization():
    if request.method == 'POST':
        name = request.form.get('name')
        org_type = request.form.get('type')
        inn = request.form.get('inn', '')
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        notes = request.form.get('notes', '')
        parent_id = request.form.get('parent_id')
        if parent_id and parent_id.isdigit():
            parent_id = int(parent_id)
        else:
            parent_id = None

        if not name:
            flash('Название организации обязательно для заполнения', 'error')
            return render_template('organizations/add_organization.html')

        try:
            org = Organization(
                name=name,
                type=org_type,
                inn=inn,
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address,
                notes=notes,
                parent_id=parent_id
            )
            db.session.add(org)
            db.session.commit()
            flash('Организация успешно добавлена!', 'success')
            return redirect(url_for('organizations.organizations'))
        except Exception as e:
            flash(f'Ошибка при добавлении организации: {str(e)}', 'error')

    # Для GET запроса – список всех организаций для выбора родителя
    all_orgs = Organization.query.order_by(Organization.name).all()
    return render_template('organizations/add_organization.html', organizations=all_orgs)

@bluprint_organizations_routes.route('/edit_organization/<int:org_id>', methods=['GET', 'POST'])
@permissions_required([Permissions.organizations_manage])
def edit_organization(org_id):
    org = Organization.query.get_or_404(org_id)

    if request.method == 'POST':
        org.name = request.form.get('name')
        org.type = request.form.get('type')
        org.inn = request.form.get('inn', '')
        org.contact_person = request.form.get('contact_person', '')
        org.phone = request.form.get('phone', '')
        org.email = request.form.get('email', '')
        org.address = request.form.get('address', '')
        org.notes = request.form.get('notes', '')
        parent_id = request.form.get('parent_id')
        if parent_id and parent_id.isdigit():
            org.parent_id = int(parent_id)
        else:
            org.parent_id = None

        if not org.name:
            flash('Название организации обязательно для заполнения', 'error')
            return render_template('organizations/edit_organization.html', org=org)

        try:
            db.session.commit()
            flash('Данные организации успешно обновлены!', 'success')
            return redirect(url_for('organizations.organizations'))
        except Exception as e:
            flash(f'Ошибка при обновлении организации: {str(e)}', 'error')

    all_orgs = Organization.query.filter(Organization.id != org_id).order_by(Organization.name).all()
    return render_template('organizations/edit_organization.html', org=org, organizations=all_orgs)

@bluprint_organizations_routes.route('/delete_organization/<int:org_id>')
@permissions_required([Permissions.organizations_manage])
def delete_organization(org_id):
    org = Organization.query.get_or_404(org_id)

    # Проверяем, используется ли организация в задачах
    tasks_count = Todo.query.filter_by(organization_id=org_id).count()
    if tasks_count > 0:
        flash('Невозможно удалить организацию, так как она используется в задачах', 'error')
        return redirect(url_for('organizations.organizations'))

    # Проверяем, есть ли дочерние организации
    children = Organization.query.filter_by(parent_id=org_id).count()
    if children > 0:
        flash('Невозможно удалить организацию, так как у неё есть дочерние организации', 'error')
        return redirect(url_for('organizations.organizations'))

    try:
        db.session.delete(org)
        db.session.commit()
        flash('Организация успешно удалена!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении организации: {str(e)}', 'error')

    return redirect(url_for('organizations.organizations'))

# ========== НОВЫЕ МАРШРУТЫ ==========

@bluprint_organizations_routes.route('/hierarchy')
@permissions_required([Permissions.organizations_manage])
def hierarchy():
    """Древовидная структура организаций"""
    root_orgs = Organization.query.filter(Organization.parent_id.is_(None)).order_by(Organization.name).all()

    def build_tree(orgs, level=0):
        result = []
        for org in orgs:
            result.append({
                'id': org.id,
                'name': org.name,
                'type': org.type,
                'level': level,
                'children': build_tree(org.children, level+1) if org.children else []
            })
        return result

    tree = build_tree(root_orgs)
    return render_template('organizations/hierarchy.html', tree=tree)

@bluprint_organizations_routes.route('/users')
@permissions_required([Permissions.organizations_manage])
def users_by_organization():
    """Просмотр пользователей по организациям"""
    orgs = db.session.query(
        Organization.id,
        Organization.name,
        func.count(User.id).label('user_count')
    ).outerjoin(User, User.organization_id == Organization.id).group_by(Organization.id).order_by(Organization.name).all()

    org_id = request.args.get('org_id', type=int)
    users = []
    selected_org = None
    if org_id:
        selected_org = Organization.query.get(org_id)
        users = User.query.filter_by(organization_id=org_id).order_by(User.username).all()

    return render_template('organizations/users_by_org.html',
                           orgs=orgs,
                           users=users,
                           selected_org=selected_org)

@bluprint_organizations_routes.route('/reports/activity')
@permissions_required([Permissions.organizations_manage])
def activity_report():
    """Отчёт по активности внутри организаций"""
    org_id = request.args.get('org_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = db.session.query(
        Log.timestamp,
        Log.user,
        Log.action,
        Organization.name.label('org_name')
    ).join(User, User.username == Log.user).join(Organization, User.organization_id == Organization.id)

    if org_id:
        query = query.filter(Organization.id == org_id)
    if date_from:
        query = query.filter(Log.timestamp >= date_from)
    if date_to:
        query = query.filter(Log.timestamp <= date_to)

    logs = query.order_by(Log.timestamp.desc()).limit(100).all()

    stats = db.session.query(
        Organization.id,
        Organization.name,
        func.count(Log.id).label('log_count'),
        func.count(distinct(User.id)).label('active_users')
    ).join(User, User.organization_id == Organization.id).join(Log, Log.user == User.username).group_by(Organization.id).order_by(func.count(Log.id).desc()).all()

    orgs = Organization.query.order_by(Organization.name).all()

    return render_template('organizations/activity_report.html',
                           logs=logs,
                           stats=stats,
                           orgs=orgs,
                           selected_org_id=org_id,
                           date_from=date_from,
                           date_to=date_to)