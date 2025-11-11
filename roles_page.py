from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from database import get_db
from database_roles import read_all_roles, save_role, update_role, find_role_by_id, remove_role
from permissions import Role, Permissions

from requirements import permissions_required

bluprint_roles_routes = Blueprint("roles", __name__)


@bluprint_roles_routes.route('/roles')
@permissions_required([Permissions.roles_read])
def roles():

    roles = read_all_roles()

    return render_template('roles/roles.html', roles=roles)

@bluprint_roles_routes.route('/create_role', methods=['GET', 'POST'])
@permissions_required([Permissions.roles_manage])
def create_role():
    if request.method == 'POST':
        try:
            role_name = request.form['name']
            role_desc = request.form['description']

            role = Role(id=None, name=role_name, description=role_desc)

            for p in Permissions:
                if p.name in request.form.keys():
                    role.add_permission(p)

            save_role(role)
        except Exception as e:
            flash(f"{e}", 'error')
        
        return redirect(url_for('roles.roles'))
    
    return render_template('roles/create_role.html', permissions=Permissions.get_names())

@bluprint_roles_routes.route('/edit_role/<int:role_id>', methods=['GET', 'POST'])
@permissions_required([Permissions.roles_manage])
def edit_role(role_id):
    if request.method == 'POST':
        role_name = request.form['name']
        role_desc = request.form['description']

        role = Role(id=role_id, name=role_name, description=role_desc)
        role.permissions.clear()
        for p in Permissions:
            if p.name in request.form.keys():
                role.add_permission(p)

        update_role(role)
        
        return redirect(url_for('roles.roles'))
    
    role:Role = find_role_by_id(role_id)
    permissions=Permissions.get_names()
    
    for p in role.permissions:
        permissions[p]['checked'] = "checked"

    return render_template('roles/edit_role.html', role=role, permissions=permissions)
        

@bluprint_roles_routes.route('/delete_role/<int:role_id>')
@permissions_required([Permissions.roles_manage])
def delete_role(role_id):
    
    remove_role(role_id)
        
    return redirect(url_for('roles.roles'))