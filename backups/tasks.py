"""backups/tasks.py — Nightly backup: single zip containing data.json + media/"""

import io
import logging
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.management import call_command

logger = logging.getLogger(__name__)

BACKUP_DIR = Path(settings.BASE_DIR) / 'backups' / 'snapshots'
RETENTION_DAYS = 30

EXCLUDED_APPS = [
    'sessions',
    'admin.logentry',
    'contenttypes',
    'auth.permission',
    'auth.group',
    'django_celery_beat',
    'django_celery_results',
]


def _stamp():
    return datetime.now().strftime('%Y%m%d_%H%M%S')


@shared_task(name='backups.tasks.nightly_backup')
def nightly_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    zip_path = BACKUP_DIR / f'backup_{stamp}.zip'

    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:

        # ── data.json ──────────────────────────────────────────────────────
        buf = io.StringIO()
        call_command(
            'dumpdata',
            *[f'--exclude={app}' for app in EXCLUDED_APPS],
            '--indent=2',
            '--natural-foreign',
            '--natural-primary',
            stdout=buf,
            verbosity=0,
        )
        zf.writestr('data.json', buf.getvalue())
        logger.info('data.json written to %s', zip_path.name)

        # ── media/ ─────────────────────────────────────────────────────────
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            for file in media_root.rglob('*'):
                if file.is_file():
                    zf.write(file, arcname='media/' + str(file.relative_to(media_root)))
            logger.info('media/ written to %s', zip_path.name)

    # ── Prune old backups ──────────────────────────────────────────────────
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    for f in BACKUP_DIR.iterdir():
        if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()
            logger.info('Pruned: %s', f.name)

    return f'Backup complete: {zip_path.name}'
