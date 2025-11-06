from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from database import get_db
from database_roles import read_all_roles


bluprint_roles_routes = Blueprint("roles", __name__)


@bluprint_roles_routes.route('/roles')
def roles():

    roles = read_all_roles()

    return render_template('roles.html', roles=roles)
