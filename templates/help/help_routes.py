from flask import Blueprint, render_template, request, jsonify
from templates.base.database_helper import db
from templates.base.requirements import login_required, permissions_required, get_current_user
from templates.roles.permissions import Permissions
from models import HelpSection, HelpBlock
from .help_data import get_help_for_endpoint, HELP_CONTENT

bluprint_help_routes = Blueprint('help', __name__, url_prefix='/help')


@bluprint_help_routes.route('/')
@login_required
def index():
    """Список всех разделов справки."""
    sections = HelpSection.query.order_by(HelpSection.title).all()
    return render_template('help/index.html', sections=sections)


@bluprint_help_routes.route('/section/<key>')
@login_required
def section(key):
    """Просмотр конкретного раздела справки."""
    data = HelpSection.query.filter_by(key=key).first()
    if not data:
        return render_template('help/not_found.html', key=key), 404
    all_sections = HelpSection.query.order_by(HelpSection.title).all()
    return render_template('help/section.html', key=key, section=data, help_all=all_sections)


@bluprint_help_routes.route('/api/for-endpoint')
@login_required
def api_for_endpoint():
    """Возвращает справку для текущего endpoint."""
    endpoint = request.args.get('endpoint', '')
    key = get_help_for_endpoint(endpoint)
    if not key:
        return jsonify({'found': False})
    section = HelpSection.query.filter_by(key=key).first()
    if not section:
        return jsonify({'found': False})
    blocks = [{'title': b.title, 'content': b.content} for b in section.blocks]
    return jsonify({
        'found': True,
        'key': section.key,
        'title': section.title,
        'icon': section.icon,
        'description': section.description or '',
        'sections': blocks
    })


# ========== РЕДАКТИРОВАНИЕ (только админы) ==========

@bluprint_help_routes.route('/admin/edit/<key>', methods=['GET', 'POST'])
@login_required
@permissions_required([Permissions.roles_manage])
def edit_section(key):
    """Редактирование раздела справки."""
    section = HelpSection.query.filter_by(key=key).first()
    if not section:
        return render_template('help/not_found.html', key=key), 404

    if request.method == 'POST':
        section.title = request.form.get('title', section.title)
        section.icon = request.form.get('icon', section.icon)
        section.description = request.form.get('description', '')

        # Удаляем все старые блоки и создаём новые
        HelpBlock.query.filter_by(section_id=section.id).delete()

        block_titles = request.form.getlist('block_title[]')
        block_contents = request.form.getlist('block_content[]')

        for idx, (t, c) in enumerate(zip(block_titles, block_contents)):
            if t.strip() and c.strip():
                db.session.add(HelpBlock(
                    section_id=section.id,
                    title=t.strip(),
                    content=c.strip(),
                    order_index=idx
                ))

        user = get_current_user()
        if user:
            section.updated_by = user.id

        db.session.commit()
        return redirect(url_for('help.section', key=key))

    return render_template('help/edit_section.html', section=section)


@bluprint_help_routes.route('/admin/create', methods=['GET', 'POST'])
@login_required
@permissions_required([Permissions.roles_manage])
def create_section():
    """Создание нового раздела справки."""
    if request.method == 'POST':
        key = request.form.get('key', '').strip().lower().replace(' ', '_')
        title = request.form.get('title', '').strip()
        icon = request.form.get('icon', 'bi-question-circle')
        description = request.form.get('description', '')

        if not key or not title:
            return render_template('help/edit_section.html', section=None, error='Заполните ключ и название')

        if HelpSection.query.filter_by(key=key).first():
            return render_template('help/edit_section.html', section=None, error='Раздел с таким ключом уже существует')

        section = HelpSection(key=key, title=title, icon=icon, description=description)
        db.session.add(section)
        db.session.flush()

        block_titles = request.form.getlist('block_title[]')
        block_contents = request.form.getlist('block_content[]')
        for idx, (t, c) in enumerate(zip(block_titles, block_contents)):
            if t.strip() and c.strip():
                db.session.add(HelpBlock(
                    section_id=section.id,
                    title=t.strip(),
                    content=c.strip(),
                    order_index=idx
                ))

        db.session.commit()
        return redirect(url_for('help.section', key=section.key))

    return render_template('help/edit_section.html', section=None)


@bluprint_help_routes.route('/admin/delete/<key>', methods=['POST'])
@login_required
@permissions_required([Permissions.roles_manage])
def delete_section(key):
    """Удаление раздела справки."""
    section = HelpSection.query.filter_by(key=key).first()
    if section:
        db.session.delete(section)
        db.session.commit()
    return redirect(url_for('help.index'))