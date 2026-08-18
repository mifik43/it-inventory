
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import SocialPost, ScheduledPost, SocialPlatform
from templates.base.database_helper import db
from templates.base.requirements import login_required, get_current_user
from .social_manager import SocialMediaManager
from sqlalchemy import func
from datetime import datetime
import json

bluprint_social_routes = Blueprint('social', __name__, url_prefix='/social')

@bluprint_social_routes.route('/history')
@login_required
def social_history():
    user = get_current_user()
    posts = SocialPost.query.filter_by(user_id=user.id).order_by(SocialPost.published_at.desc()).all()
    available_platforms = SocialMediaManager().get_available_platforms()
    return render_template('social/history.html', posts=posts, available_platforms=available_platforms)

@bluprint_social_routes.route('/scheduled')
@login_required
def scheduled_posts():
    user = get_current_user()
    posts = ScheduledPost.query.filter_by(user_id=user.id).order_by(ScheduledPost.scheduled_time.asc()).all()
    return render_template('social/scheduled.html', scheduled_posts=posts)

@bluprint_social_routes.route('/platforms')
@login_required
def social_platforms():
    user = get_current_user()
    platforms = SocialPlatform.query.filter_by(user_id=user.id).all()
    return render_template('social/platforms.html', platforms=platforms)

@bluprint_social_routes.route('/platforms/add', methods=['GET', 'POST'])
@login_required
def add_platform():
    user = get_current_user()
    if request.method == 'POST':
        platform = SocialPlatform(
            platform_name=request.form.get('platform_name'),
            platform_type=request.form.get('platform_type'),
            api_key=request.form.get('api_key'),
            api_secret=request.form.get('api_secret'),
            access_token=request.form.get('access_token'),
            token_secret=request.form.get('token_secret'),
            group_id=request.form.get('group_id'),
            channel_id=request.form.get('channel_id'),
            is_active=request.form.get('is_active') == 'on',
            user_id=user.id
        )
        db.session.add(platform)
        db.session.commit()
        flash('Платформа добавлена', 'success')
        return redirect(url_for('social.social_platforms'))
    return render_template('social/add_platform.html')

@bluprint_social_routes.route('/platforms/<int:platform_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_platform(platform_id):
    user = get_current_user()
    platform = SocialPlatform.query.get_or_404(platform_id)
    if platform.user_id != user.id:
        flash('Нет прав', 'error')
        return redirect(url_for('social.social_platforms'))
    if request.method == 'POST':
        platform.platform_name = request.form.get('platform_name')
        platform.platform_type = request.form.get('platform_type')
        platform.api_key = request.form.get('api_key')
        platform.api_secret = request.form.get('api_secret')
        platform.access_token = request.form.get('access_token')
        platform.token_secret = request.form.get('token_secret')
        platform.group_id = request.form.get('group_id')
        platform.channel_id = request.form.get('channel_id')
        platform.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash('Платформа обновлена', 'success')
        return redirect(url_for('social.social_platforms'))
    return render_template('social/edit_platform.html', platform=platform)

@bluprint_social_routes.route('/platforms/<int:platform_id>/delete')
@login_required
def delete_platform(platform_id):
    user = get_current_user()
    platform = SocialPlatform.query.get_or_404(platform_id)
    if platform.user_id != user.id:
        flash('Нет прав', 'error')
        return redirect(url_for('social.social_platforms'))
    db.session.delete(platform)
    db.session.commit()
    flash('Платформа удалена', 'success')
    return redirect(url_for('social.social_platforms'))

@bluprint_social_routes.route('/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    user = get_current_user()
    post = SocialPost.query.get_or_404(post_id)
    if post.user_id != user.id:
        flash('Нет прав', 'error')
        return redirect(url_for('social.social_history'))
    db.session.delete(post)
    db.session.commit()
    flash('Публикация удалена', 'success')
    return redirect(url_for('social.social_history'))

@bluprint_social_routes.route('/cancel_scheduled/<int:post_id>')
@login_required
def cancel_scheduled(post_id):
    user = get_current_user()
    post = ScheduledPost.query.get_or_404(post_id)
    if post.user_id != user.id:
        flash('Нет прав', 'error')
        return redirect(url_for('social.scheduled_posts'))
    db.session.delete(post)
    db.session.commit()
    flash('Запланированная публикация отменена', 'success')
    return redirect(url_for('social.scheduled_posts'))