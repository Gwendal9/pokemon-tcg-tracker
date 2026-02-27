"""tracker/backup.py — Sauvegarde automatique de la DB au démarrage."""
import logging
import os
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

MAX_BACKUPS = 5


def backup_db(db_path: str, data_dir: str) -> None:
    """Copie db_path dans data_dir/backups/ avec timestamp.

    Conserve seulement les MAX_BACKUPS fichiers les plus récents.
    Silencieux en cas d'erreur — ne bloque jamais le démarrage.
    """
    try:
        if not os.path.exists(db_path):
            return
        backup_dir = os.path.join(data_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dest = os.path.join(backup_dir, f"tracker_{timestamp}.db")
        shutil.copy2(db_path, dest)
        logger.info("Backup DB : %s", dest)
        # Supprimer les anciens backups au-delà de MAX_BACKUPS
        backups = sorted(
            os.path.join(backup_dir, f)
            for f in os.listdir(backup_dir)
            if f.startswith("tracker_") and f.endswith(".db")
        )
        for old in backups[:-MAX_BACKUPS]:
            os.remove(old)
            logger.debug("Ancien backup supprimé : %s", old)
    except Exception as e:
        logger.warning("backup_db: %s", e)
