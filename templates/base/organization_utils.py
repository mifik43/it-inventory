from models import Organization
from logger import logger
from templates.auth.users import User
from templates.base.requirements import get_current_user_permissions
from templates.roles.permissions import Permissions
ALL_ORGANIZATIONS = 'all'  # Специальное значение для режима "все организации"

def get_user_visible_organizations(user:User):
    """
    Возвращает список организаций, доступных пользователю.
    Для суперадмина добавляется специальный элемент 'Все организации'.
    """
    
    user_permissions = get_current_user_permissions()
    if Permissions.organizations_manage_all in user_permissions:
        orgs = Organization.query.all()
        # Добавляем специальный элемент в начало списка
        return [{'id': ALL_ORGANIZATIONS, 'name': 'Все организации'}] + orgs
    orgs = set()
    main_org = Organization.query.get(user.organization_id)
    if main_org:
        orgs.add(main_org)

        if Permissions.organizations_manage_children in user_permissions:
            children = get_all_children(main_org)
            orgs.update(children)
    return list(orgs)

def get_all_children(org):
    result = []
    for child in org.children:
        result.append(child)
        result.extend(get_all_children(child))
    return result

def filter_by_organization(query, model_class, org_id):
    """
    Универсальный фильтр для запросов по организации.
    Если org_id == ALL_ORGANIZATIONS, фильтрация не применяется.
    """
    if org_id == ALL_ORGANIZATIONS:
        return query
    if org_id:
        return query.filter(model_class.organization_id == org_id)
    return query.filter(model_class.organization_id.is_(None))