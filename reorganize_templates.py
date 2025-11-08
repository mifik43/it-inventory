import os
import shutil

def reorganize_templates():
    # Создаем структуру папок
    folders = [
        'templates/base',
        'templates/auth', 
        'templates/devices',
        'templates/providers',
        'templates/cubes',
        'templates/organizations',
        'templates/todo',
        'templates/knowledge/articles',
        'templates/knowledge/notes',
        'templates/shifts',
        'templates/dashboard'
    ]
    
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ Создана папка: {folder}")
    
    # Сопоставление файлов и их новых путей
    file_mapping = {
        # Base
        'templates/base.html': 'templates/base/base.html',
        'templates/navigation.html': 'templates/base/navigation.html',
        
        # Auth
        'templates/login.html': 'templates/auth/login.html',
        'templates/change_password.html': 'templates/auth/change_password.html',
        'templates/create_user.html': 'templates/auth/create_user.html',
        'templates/edit_user.html': 'templates/auth/edit_user.html',
        'templates/users.html': 'templates/auth/users.html',
        
        # Devices
        'templates/devices.html': 'templates/devices/devices.html',
        'templates/add_device.html': 'templates/devices/add_device.html',
        'templates/edit_device.html': 'templates/devices/edit_device.html',
        
        # Providers
        'templates/providers.html': 'templates/providers/providers.html',
        'templates/add_provider.html': 'templates/providers/add_provider.html',
        'templates/edit_provider.html': 'templates/providers/edit_provider.html',
        
        # Cubes
        'templates/cubes.html': 'templates/cubes/cubes.html',
        'templates/add_cube.html': 'templates/cubes/add_cube.html',
        'templates/edit_cube.html': 'templates/cubes/edit_cube.html',
        
        # Organizations
        'templates/organizations.html': 'templates/organizations/organizations.html',
        'templates/add_organization.html': 'templates/organizations/add_organization.html',
        'templates/edit_organization.html': 'templates/organizations/edit_organization.html',
        
        # TODO
        'templates/todo.html': 'templates/todo/todo.html',
        'templates/add_todo.html': 'templates/todo/add_todo.html',
        'templates/edit_todo.html': 'templates/todo/edit_todo.html',
        
        # Knowledge - Articles
        'templates/articles.html': 'templates/knowledge/articles/articles.html',
        'templates/view_article.html': 'templates/knowledge/articles/view_article.html',
        'templates/add_article.html': 'templates/knowledge/articles/add_article.html',
        'templates/edit_article.html': 'templates/knowledge/articles/edit_article.html',
        
        # Knowledge - Notes
        'templates/notes.html': 'templates/knowledge/notes/notes.html',
        'templates/add_note.html': 'templates/knowledge/notes/add_note.html',
        'templates/edit_note.html': 'templates/knowledge/notes/edit_note.html',
        
        # Shifts
        'templates/shifts.html': 'templates/shifts/shifts.html',
        'templates/add_shift.html': 'templates/shifts/add_shift.html',
        'templates/edit_shift.html': 'templates/shifts/edit_shift.html',
        
        # Dashboard
        'templates/index.html': 'templates/dashboard/index.html'

        # roles
        'roles/roles.html': 'templates/roles/roles.html',
        'roles/create_role.html': 'templates/roles/create_role.html',
        'roles/edit_role.html': 'templates/roles/edit_role.html'

        # Internet
        'internet/internet.html': 'templates/internet/internet.html'
    }
    
    # Перемещаем файлы
    moved_count = 0
    for old_path, new_path in file_mapping.items():
        if os.path.exists(old_path):
            shutil.move(old_path, new_path)
            print(f"✅ Перемещен: {old_path} -> {new_path}")
            moved_count += 1
        else:
            print(f"⚠️  Файл не найден: {old_path}")
    
    print(f"\n🎉 Реорганизация завершена! Перемещено файлов: {moved_count}")

if __name__ == '__main__':
    reorganize_templates()