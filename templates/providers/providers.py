from datetime import datetime

from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from sqlalchemy import or_

from templates.base.database_helper import db
from templates.base.requirements import permissions_required, permissions_required_all, permissions_required
from templates.roles.permissions import Permissions
from logger import logger
from models import Provider

bluprint_provider_routes = Blueprint("providers", __name__)


def parse_date(date_string):
    if not date_string:
        return None
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        logger.warning(f'Неверный формат даты для провайдера: {date_string}')
        return None


@bluprint_provider_routes.route('/providers')
@permissions_required([Permissions.providers_read])
def providers():
    providers_list = Provider.query.order_by(Provider.created_at.desc()).all()
    logger.info(f'Открыт список провайдеров, найдено {len(providers_list)}')
    return render_template('providers/providers.html', providers=providers_list)


@bluprint_provider_routes.route('/add_provider', methods=['GET', 'POST'])
@permissions_required([Permissions.providers_manage])
def add_provider():
    logger.info('Открыта страница добавления провайдера')
    if request.method == 'POST':
        logger.info('Запрос на добавление провайдера получен')
        name = request.form['name']
        service_type = request.form['service_type']
        contract_number = request.form.get('contract_number', '')
        contract_date = request.form.get('contract_date', '')
        ip_range = request.form.get('ip_range', '')
        speed = request.form.get('speed', '')
        price = request.form.get('price', 0)
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        object_location = request.form['object_location']
        city = request.form['city']
        status = request.form['status']
        notes = request.form.get('notes', '')

        try:
            price = float(price) if price else None
        except ValueError:
            price = None
            logger.warning(f'Неверная цена провайдера: {request.form.get("price", "")}')

        contract_date_obj = parse_date(contract_date)

        try:
            logger.debug(f'Параметры нового провайдера: name={name}, service_type={service_type}, object_location={object_location}, city={city}, status={status}')
            provider = Provider(
                name=name,
                service_type=service_type,
                contract_number=contract_number,
                contract_date=contract_date_obj,
                ip_range=ip_range,
                speed=speed,
                price=price,
                contact_person=contact_person,
                phone=phone,
                email=email,
                object_location=object_location,
                city=city,
                status=status,
                notes=notes
            )
            db.session.add(provider)
            db.session.commit()
            logger.info(f'Провайдер добавлен: id={provider.id} name={provider.name}')
            flash('Провайдер успешно добавлен!', 'success')
            return redirect(url_for('providers.providers'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Ошибка при добавлении провайдера: {e}', exc_info=True)
            flash(f'Ошибка при добавлении провайдера: {str(e)}', 'error')

    return render_template('providers/add_provider.html')


@bluprint_provider_routes.route('/edit_provider/<int:provider_id>', methods=['GET', 'POST'])
@permissions_required([Permissions.providers_manage])
def edit_provider(provider_id):
    logger.info(f'Открыта страница редактирования провайдера: id={provider_id}')
    provider = Provider.query.get(provider_id)
    if not provider:
        logger.warning(f'Провайдер не найден для редактирования: id={provider_id}')
        flash('Провайдер не найден', 'error')
        return redirect(url_for('providers.providers'))

    if request.method == 'POST':
        logger.info(f'Запрос на обновление провайдера получен: id={provider_id}')
        name = request.form['name']
        service_type = request.form['service_type']
        contract_number = request.form.get('contract_number', '')
        contract_date = request.form.get('contract_date', '')
        ip_range = request.form.get('ip_range', '')
        speed = request.form.get('speed', '')
        price = request.form.get('price', 0)
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        object_location = request.form['object_location']
        city = request.form['city']
        status = request.form['status']
        notes = request.form.get('notes', '')

        try:
            price = float(price) if price else None
        except ValueError:
            price = None
            logger.warning(f'Неверная цена провайдера при редактировании: {request.form.get("price", "")}')

        contract_date_obj = parse_date(contract_date)

        try:
            logger.debug(f'Новые данные провайдера id={provider_id}: name={name}, service_type={service_type}, object_location={object_location}, city={city}, status={status}')
            provider.name = name
            provider.service_type = service_type
            provider.contract_number = contract_number
            provider.contract_date = contract_date_obj
            provider.ip_range = ip_range
            provider.speed = speed
            provider.price = price
            provider.contact_person = contact_person
            provider.phone = phone
            provider.email = email
            provider.object_location = object_location
            provider.city = city
            provider.status = status
            provider.notes = notes
            db.session.commit()
            logger.info(f'Провайдер обновлен: id={provider.id} name={provider.name}')
            flash('Данные провайдера успешно обновлены!', 'success')
            return redirect(url_for('providers.providers'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Ошибка при обновлении провайдера id={provider_id}: {e}', exc_info=True)
            flash(f'Ошибка при обновлении провайдера: {str(e)}', 'error')

    return render_template('providers/edit_provider.html', provider=provider)


@bluprint_provider_routes.route('/delete_provider/<int:provider_id>')
@permissions_required([Permissions.providers_manage])
def delete_provider(provider_id):
    logger.info(f'Запрос на удаление провайдера: id={provider_id}')
    provider = Provider.query.get(provider_id)
    if not provider:
        logger.warning(f'Провайдер не найден для удаления: id={provider_id}')
        flash('Провайдер не найден', 'error')
        return redirect(url_for('providers.providers'))

    try:
        logger.info(f'Удаление провайдера: id={provider_id} name={provider.name}')
        db.session.delete(provider)
        db.session.commit()
        flash('Провайдер успешно удален!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Ошибка при удалении провайдера id={provider_id}: {e}', exc_info=True)
        flash(f'Ошибка при удалении провайдера: {str(e)}', 'error')

    return redirect(url_for('providers.providers'))


@bluprint_provider_routes.route('/provider_search')
@permissions_required([Permissions.providers_read])
def provider_search():
    query = request.args.get('q', '')
    logger.info(f'Запрос на поиск провайдеров: query="{query}"')
    search_value = f'%{query}%'
    providers_list = Provider.query.filter(
        or_(
            Provider.name.ilike(search_value),
            Provider.contract_number.ilike(search_value),
            Provider.object_location.ilike(search_value),
            Provider.city.ilike(search_value),
            Provider.contact_person.ilike(search_value)
        )
    ).order_by(Provider.created_at.desc()).all()
    logger.info(f'Поиск провайдеров query="{query}", найдено {len(providers_list)}')
    return render_template('providers/providers.html', providers=providers_list, search_query=query)
