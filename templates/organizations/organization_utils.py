from models import Organization

ALL_ORGANIZATIONS = 'all'

def get_user_visible_organizations(user):
    """
    Возвращает список организаций, доступных пользователю.
    """
    print(f"[DEBUG] get_user_visible_organizations called for user: {user.username}, org_id: {user.organization_id}")

    # Обычный пользователь
    if user.organization_id:
        org = Organization.query.get(user.organization_id)
        if org:
            print("[DEBUG] user: found 1 org")
            return [org]
    print("[DEBUG] user: no org")
    return []

def get_all_children(org):
    result = []
    for child in org.children:
        result.append(child)
        result.extend(get_all_children(child))
    return result

def filter_by_organization(query, model_class, org_id, user_role=None):
    if org_id == ALL_ORGANIZATIONS:
        return query
    if org_id:
        return query.filter(model_class.organization_id == org_id)
    return query.filter(model_class.organization_id.is_(None))