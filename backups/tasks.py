"""backups/tasks.py — Nightly backup: database + media files."""

import os
import shutil
import subprocess
import tarfile
import logging
from datetime import datetime, timedelta
from pathlib import Path

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

# Where backups are stored on the server
BACKUP_DIR = Path(settings.BASE_DIR) / 'backups' / 'snapshots'

# Tables excluded from the DB dump (sessions, logs, cache, celery noise)
EXCLUDED_TABLES = [
    'django_session',
    'django_admin_log',
    'django_content_type',
    'auth_permission',
    'auth_group',
    'auth_group_permissions',
    'auth_user_groups',
    'auth_user_user_permissions',
    'django_celery_beat_clockedschedule',
    'django_celery_beat_crontabschedule',
    'django_celery_beat_intervalschedule',
    'django_celery_beat_periodictask',
    'django_celery_beat_periodictasks',
    'django_celery_beat_solarschedule',
    'django_celery_results_taskresult',
    'django_celery_results_groupresult',
    'django_celery_results_chordcounter',
]

# Keep last N days of backups
RETENTION_DAYS = 30


def _stamp():
    return datetime.now().strftime('%Y%m%d_%H%M%S')


@shared_task(name='backups.tasks.nightly_backup')
def nightly_backup():
    """
    Runs at midnight EAT.
    1. DB dump (PostgreSQL), excluding noise tables.
    2. Media files archive.
    3. Prunes snapshots older than RETENTION_DAYS.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    errors = []

    # ── 1. Database backup ─────────────────────────────────────────────────
    db = settings.DATABASES['default']

    if db['ENGINE'] == 'django.db.backends.postgresql':
        dump_path = BACKUP_DIR / f'db_{stamp}.sql.gz'
        exclude_args = []
        for table in EXCLUDED_TABLES:
            exclude_args += ['--exclude-table', table]

        env = os.environ.copy()
        env['PGPASSWORD'] = db['PASSWORD']

        pg_cmd = [
            'pg_dump',
            '-h', db.get('HOST', 'localhost'),
            '-p', str(db.get('PORT', 5432)),
            '-U', db['USER'],
            *exclude_args,
            db['NAME'],
        ]

        try:
            with open(dump_path, 'wb') as f:
                pg = subprocess.Popen(pg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                gzip = subprocess.Popen(['gzip'], stdin=pg.stdout, stdout=f, stderr=subprocess.PIPE)
                pg.stdout.close()
                _, gzip_err = gzip.communicate()
                pg.wait()
                if pg.returncode != 0:
                    raise RuntimeError(f'pg_dump exited {pg.returncode}')
            logger.info('DB backup: %s', dump_path.name)
        except Exception as exc:
            errors.append(f'DB backup failed: {exc}')
            logger.error('DB backup failed: %s', exc)
            if dump_path.exists():
                dump_path.unlink()

    elif db['ENGINE'] == 'django.db.backends.sqlite3':
        src = Path(db['NAME'])
        dst = BACKUP_DIR / f'db_{stamp}.sqlite3'
        try:
            shutil.copy2(src, dst)
            logger.info('SQLite backup: %s', dst.name)
        except Exception as exc:
            errors.append(f'SQLite backup failed: {exc}')
            logger.error('SQLite backup failed: %s', exc)

    # ── 2. Media backup ────────────────────────────────────────────────────
    media_root = Path(settings.MEDIA_ROOT)
    if media_root.exists() and any(media_root.iterdir()):
        archive_path = BACKUP_DIR / f'media_{stamp}.tar.gz'
        try:
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(media_root, arcname='media')
            logger.info('Media backup: %s', archive_path.name)
        except Exception as exc:
            errors.append(f'Media backup failed: {exc}')
            logger.error('Media backup failed: %s', exc)
    else:
        logger.info('Media directory empty or missing — skipped.')

    # ── 3. Prune old backups ───────────────────────────────────────────────
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    for f in BACKUP_DIR.iterdir():
        if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()
            logger.info('Pruned old backup: %s', f.name)

    if errors:
        raise RuntimeError('Backup completed with errors: ' + ' | '.join(errors))

    return f'Backup complete [{stamp}]'
