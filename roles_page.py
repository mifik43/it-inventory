from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from database import get_db
from database_roles import read_all_roles, save_role
from permissions import Role


bluprint_roles_routes = Blueprint("roles", __name__)


@bluprint_roles_routes.route('/roles')
def roles():

    roles = read_all_roles()

    return render_template('roles.html', roles=roles)

@bluprint_roles_routes.route('/create_role', methods=['GET', 'POST'])
def create_role():
    if request.method == 'POST':
        role_name = request.form['name']
        role_desc = request.form['description']

        role = Role(id=None, name=role_name, description=role_desc)
        save_role(role)
        
        return redirect(url_for('roles.roles'))
    
    return render_template('create_role.html')
        
