import subprocess
import tempfile
import os
import time
from datetime import datetime

def execute_script(script_content, script_type='bat'):
    """
    Выполняет скрипт и возвращает результат
    """
    try:
        # Создаем временный файл для скрипта
        with tempfile.NamedTemporaryFile(mode='w', 
                                       suffix=f'.{script_type}', 
                                       delete=False,
                                       encoding='utf-8') as temp_file:
            temp_file.write(script_content)
            temp_file.flush()
            temp_path = temp_file.name
        
        # Выполняем скрипт
        start_time = time.time()
        
        if script_type == 'bat':
            result = subprocess.run(
                ['cmd', '/c', temp_path],
                capture_output=True,
                text=True,
                timeout=300,  # 5 минут таймаут
                encoding='cp866'  # Кодировка для русских символов в Windows
            )
        elif script_type == 'ps1':
            result = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-File', temp_path],
                capture_output=True,
                text=True,
                timeout=300,
                encoding='cp866'
            )
        else:
            raise ValueError(f"Unsupported script type: {script_type}")
        
        execution_time = time.time() - start_time
        
        # Очищаем временный файл
        try:
            os.unlink(temp_path)
        except:
            pass
        
        # Определяем успешность выполнения
        success = result.returncode == 0
        
        return {
            'success': success,
            'output': result.stdout,
            'error': result.stderr,
            'return_code': result.returncode,
            'execution_time': execution_time
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': '',
            'error': 'Script execution timeout (5 minutes)',
            'return_code': -1,
            'execution_time': 300
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'error': str(e),
            'return_code': -1,
            'execution_time': 0
        }

def save_script_result(db, script_id, result):
    """
    Сохраняет результат выполнения скрипта в базу данных
    """
    db.execute('''
        INSERT INTO script_results 
        (script_id, output, success, error_message, execution_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        script_id,
        result['output'],
        result['success'],
        result['error'],
        result['execution_time']
    ))
    db.commit()

def get_script_results(db, script_id, limit=10):
    """
    Получает историю выполнения скрипта
    """
    return db.execute('''
        SELECT * FROM script_results 
        WHERE script_id = ? 
        ORDER BY executed_at DESC 
        LIMIT ?
    ''', (script_id, limit)).fetchall()