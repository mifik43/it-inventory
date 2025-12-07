@bluprint_provider_routes.route('/providers')
@permission_required(Permissions.providers_read)
def providers():
    db = get_db()
    user_id = session.get('user_id')
    
    organization_filter = request.args.get('organization_id', type=int)
    
    query = '''
        SELECT p.*, o.name as organization_name 
        FROM providers p
        LEFT JOIN organizations o ON p.organization_id = o.id
    '''
    params = []
    
    where_clauses = []
    
    if session.get('role') not in ['admin', 'manager']:
        where_clauses.append('''
            (p.organization_id IN (
                SELECT organization_id FROM user_organizations WHERE user_id = ?
            ) OR p.organization_id IS NULL)
        ''')
        params.append(user_id)
    
    if organization_filter:
        where_clauses.append('p.organization_id = ?')
        params.append(organization_filter)
    
    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)
    
    query += ' ORDER BY p.name'
    
    providers_list = db.execute(query, tuple(params)).fetchall()
    
    organizations = get_user_organizations_list(user_id, include_all=True)
    
    return render_template('providers/providers.html', 
                         providers=providers_list,
                         organizations=organizations,
                         selected_org=organization_filter)

@bluprint_provider_routes.route('/add_provider', methods=['GET', 'POST'])
@permission_required(Permissions.providers_manage)
def add_provider():
    db = get_db()
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        # ... существующий код ...
        organization_id = request.form.get('organization_id', None)
        
        if organization_id and not has_organization_access(user_id, organization_id):
            flash('У вас нет доступа к выбранной организации', 'error')
            return redirect(url_for('providers.add_provider'))
        
        # Добавьте organization_id в INSERT запрос
        db.execute('''
            INSERT INTO providers (..., organization_id, created_by)
            VALUES (..., ?, ?)
        ''', (..., organization_id, user_id))
        # ...
    
    organizations = get_user_organizations_list(user_id)
    return render_template('providers/add_provider.html', organizations=organizations)