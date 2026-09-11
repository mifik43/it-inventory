# templates/monitoring/db_monitoring.py
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify
from sqlalchemy import text
from templates.base.database_helper import db
from templates.base.requirements import permissions_required
from templates.roles.permissions import Permissions

bluprint_db_monitoring = Blueprint('db_monitoring', __name__, url_prefix='/monitoring/db')

# Порог для «медленного» запроса (в секундах)
SLOW_QUERY_THRESHOLD_SEC = 1.0


def _fetchall(query, params=None):
    """Универсальный помощник."""
    try:
        result = db.session.execute(text(query), params or {})
        return [dict(row._mapping) for row in result]
    except Exception as e:
        db.session.rollback()
        return [{'error': str(e)}]


def _fetchone(query, params=None):
    rows = _fetchall(query, params)
    return rows[0] if rows else {}


# ========== СБОР ДАННЫХ ==========

def get_db_size():
    """Размер текущей базы данных."""
    row = _fetchone("SELECT pg_size_pretty(pg_database_size(current_database())) AS pretty, "
                    "pg_database_size(current_database()) AS bytes")
    return {
        'size_pretty': row.get('pretty', '—'),
        'size_bytes': row.get('bytes', 0),
        'size_mb': round((row.get('bytes') or 0) / (1024 ** 2), 2),
    }


def get_top_tables(limit=15):
    """Топ таблиц по размеру."""
    return _fetchall(f"""
        SELECT
            schemaname || '.' || relname AS table_name,
            pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
            pg_size_pretty(pg_relation_size(relid)) AS table_size,
            pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS indexes_size,
            pg_total_relation_size(relid) AS total_bytes,
            n_live_tup AS row_count
        FROM pg_stat_user_tables
        ORDER BY pg_total_relation_size(relid) DESC
        LIMIT {int(limit)}
    """)


def get_connections():
    """Активные соединения."""
    total = _fetchone("SELECT count(*) AS cnt FROM pg_stat_activity WHERE datname = current_database()")
    by_state = _fetchall("""
        SELECT COALESCE(state, 'unknown') AS state, count(*) AS cnt
        FROM pg_stat_activity
        WHERE datname = current_database()
        GROUP BY state
        ORDER BY cnt DESC
    """)
    by_user = _fetchall("""
        SELECT COALESCE(usename, '—') AS usename, count(*) AS cnt
        FROM pg_stat_activity
        WHERE datname = current_database()
        GROUP BY usename
        ORDER BY cnt DESC
    """)
    max_conn = _fetchone("SHOW max_connections")
    max_conn_val = int(max_conn.get('max_connections', 100)) if 'max_connections' in max_conn else 100
    used = total.get('cnt', 0)
    return {
        'total': used,
        'max': max_conn_val,
        'percent': round(used / max_conn_val * 100, 1) if max_conn_val else 0,
        'by_state': by_state,
        'by_user': by_user,
    }


def get_active_queries():
    """Запросы, выполняющиеся прямо сейчас."""
    return _fetchall("""
        SELECT
            pid,
            usename AS username,
            application_name,
            client_addr::text AS client_addr,
            state,
            EXTRACT(EPOCH FROM (now() - query_start))::numeric(10,2) AS duration_sec,
            COALESCE(LEFT(query, 200), '') AS query
        FROM pg_stat_activity
        WHERE datname = current_database()
          AND state != 'idle'
          AND pid != pg_backend_pid()
        ORDER BY query_start ASC
    """)


def get_slow_queries(limit=20):
    """Медленные запросы из pg_stat_statements (если расширение установлено)."""
    # Проверяем, установлено ли расширение
    check = _fetchone("""
        SELECT EXISTS (
            SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
        ) AS installed
    """)
    if not check.get('installed'):
        return {'installed': False, 'queries': []}

    queries = _fetchall(f"""
        SELECT
            queryid,
            calls,
            ROUND(total_exec_time::numeric, 2) AS total_time_ms,
            ROUND(mean_exec_time::numeric, 2) AS mean_time_ms,
            ROUND(max_exec_time::numeric, 2) AS max_time_ms,
            rows,
            LEFT(query, 300) AS query
        FROM pg_stat_statements
        WHERE mean_exec_time > {SLOW_QUERY_THRESHOLD_SEC * 1000}
        ORDER BY mean_exec_time DESC
        LIMIT {int(limit)}
    """)
    return {'installed': True, 'queries': queries}


def get_table_stats(limit=15):
    """Статистика по таблицам: чтение/запись строк, dead tuples."""
    return _fetchall(f"""
        SELECT
            schemaname || '.' || relname AS table_name,
            seq_scan,
            seq_tup_read,
            COALESCE(idx_scan, 0) AS idx_scan,
            n_tup_ins AS inserts,
            n_tup_upd AS updates,
            n_tup_del AS deletes,
            n_live_tup AS live_rows,
            n_dead_tup AS dead_rows,
            last_vacuum,
            last_autovacuum,
            last_analyze
        FROM pg_stat_user_tables
        ORDER BY (n_tup_ins + n_tup_upd + n_tup_del) DESC
        LIMIT {int(limit)}
    """)


def get_cache_hit_ratio():
    """Кэш-хит базы данных."""
    row = _fetchone("""
        SELECT
            ROUND(
                100.0 * sum(blks_hit) / NULLIF(sum(blks_hit) + sum(blks_read), 0),
                2
            ) AS ratio
        FROM pg_stat_database
        WHERE datname = current_database()
    """)
    return {'ratio': row.get('ratio', 0) or 0}


def get_indexes_info(limit=10):
    """Информация об индексах — самые большие и неиспользуемые."""
    biggest = _fetchall(f"""
        SELECT
            schemaname || '.' || indexrelname AS index_name,
            pg_size_pretty(pg_relation_size(indexrelid)) AS size,
            pg_relation_size(indexrelid) AS size_bytes,
            idx_scan AS scans
        FROM pg_stat_user_indexes
        ORDER BY pg_relation_size(indexrelid) DESC
        LIMIT {int(limit)}
    """)
    unused = _fetchall(f"""
        SELECT
            schemaname || '.' || indexrelname AS index_name,
            pg_size_pretty(pg_relation_size(indexrelid)) AS size,
            idx_scan AS scans
        FROM pg_stat_user_indexes
        WHERE idx_scan = 0
          AND indexrelname NOT LIKE '%_pkey'
        ORDER BY pg_relation_size(indexrelid) DESC
        LIMIT {int(limit)}
    """)
    return {'biggest': biggest, 'unused': unused}


# ========== МАРШРУТЫ ==========

@bluprint_db_monitoring.route('/')
@permissions_required([Permissions.roles_manage])
def index():
    return render_template('monitoring/db.html')


@bluprint_db_monitoring.route('/api/summary')
@permissions_required([Permissions.roles_manage])
def api_summary():
    return jsonify({
        'size': get_db_size(),
        'connections': get_connections(),
        'cache': get_cache_hit_ratio(),
        'timestamp': datetime.now().strftime('%H:%M:%S'),
    })


@bluprint_db_monitoring.route('/api/tables')
@permissions_required([Permissions.roles_manage])
def api_tables():
    return jsonify({
        'top_tables': get_top_tables(),
        'table_stats': get_table_stats(),
    })


@bluprint_db_monitoring.route('/api/queries')
@permissions_required([Permissions.roles_manage])
def api_queries():
    return jsonify({
        'active': get_active_queries(),
        'slow': get_slow_queries(),
    })


@bluprint_db_monitoring.route('/api/indexes')
@permissions_required([Permissions.roles_manage])
def api_indexes():
    return jsonify(get_indexes_info())