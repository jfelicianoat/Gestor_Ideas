"""Backup engine: backup y restauracion versionada de la BD SQLite."""

import json as _json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger


@dataclass
class BackupEntry:
    ruta_archivo: str
    fecha_backup: datetime
    tamano_bytes: int
    id: int | None = None


class BackupEngine:
    def __init__(
        self, db_path: str | Path, backup_dir: str | Path, max_versions: int = 10
    ) -> None:
        self._db_path = Path(db_path)
        self._backup_dir = Path(backup_dir)
        self._max_versions = max_versions
        self._log = logger.bind(component="backup")

    def create_backup(self) -> BackupEntry:
        if not self._db_path.exists():
            raise FileNotFoundError(f"Base de datos no encontrada: {self._db_path}")

        self._backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_path = self._backup_dir / f"backup_{timestamp}.db"

        self._copy_sqlite_snapshot(self._db_path, backup_path)
        size = backup_path.stat().st_size

        entry = BackupEntry(
            ruta_archivo=str(backup_path),
            fecha_backup=datetime.now(UTC),
            tamano_bytes=size,
        )
        self._record_metadata(entry)
        self._prune_old_backups()
        self._log.info("Backup creado: {} ({} bytes)", backup_path.name, size)
        return entry

    def restore(self, backup_id: int | None = None) -> Path:
        entries = self.list_backups()
        if not entries:
            raise FileNotFoundError("No hay backups disponibles para restaurar")

        if backup_id is not None:
            matching = [e for e in entries if e.id == backup_id]
            if not matching:
                raise ValueError(f"No se encontro backup con id={backup_id}")
            entry = matching[0]
        else:
            entry = entries[-1]

        backup_path = Path(entry.ruta_archivo)
        if not backup_path.exists():
            raise FileNotFoundError(f"Archivo de backup no encontrado: {backup_path}")

        restored_path = self._db_path.with_suffix(".db.restored")
        self._copy_sqlite_snapshot(backup_path, restored_path)
        self._log.info(
            "Backup restaurado: {} -> {}", backup_path.name, restored_path.name
        )
        return restored_path

    def list_backups(self) -> list[BackupEntry]:
        metadata_path = self._backup_dir / ".metadata"
        if not metadata_path.exists():
            return []
        try:
            raw = _json.loads(metadata_path.read_text(encoding="utf-8"))
            return [
                BackupEntry(
                    id=e.get("id"),
                    ruta_archivo=e["ruta_archivo"],
                    fecha_backup=datetime.fromisoformat(e["fecha_backup"]),
                    tamano_bytes=e["tamano_bytes"],
                )
                for e in raw
            ]
        except (OSError, _json.JSONDecodeError, KeyError) as exc:
            self._log.warning("Metadatos de backup corruptos: {}", exc)
            return []

    def delete_backup(self, backup_id: int) -> None:
        entries = self.list_backups()
        matching = [e for e in entries if e.id == backup_id]
        if not matching:
            raise ValueError(f"No se encontro backup con id={backup_id}")

        entry = matching[0]
        path = Path(entry.ruta_archivo)
        if path.exists():
            path.unlink()

        remaining = [e for e in entries if e.id != backup_id]
        self._write_metadata(remaining)
        self._log.info("Backup eliminado: id={}", backup_id)

    def integrity_check(self) -> list[str]:
        issues: list[str] = []
        for entry in self.list_backups():
            path = Path(entry.ruta_archivo)
            if not path.exists():
                issues.append(f"Backup id={entry.id} falta el archivo: {path}")
                continue
            if path.stat().st_size == 0:
                issues.append(f"Backup id={entry.id} esta vacio: {path}")
        return issues

    def _prune_old_backups(self) -> None:
        entries = self.list_backups()
        if len(entries) <= self._max_versions:
            return
        to_remove = entries[: len(entries) - self._max_versions]
        for entry in to_remove:
            if entry.id is not None:
                self.delete_backup(entry.id)

    def _record_metadata(self, entry: BackupEntry) -> None:
        entries = self.list_backups()
        next_id = (max((e.id or 0) for e in entries) + 1) if entries else 1
        entry.id = next_id
        entries.append(entry)
        self._write_metadata(entries)

    def _write_metadata(self, entries: list[BackupEntry]) -> None:
        raw = [
            {
                "id": e.id,
                "ruta_archivo": e.ruta_archivo,
                "fecha_backup": e.fecha_backup.isoformat(),
                "tamano_bytes": e.tamano_bytes,
            }
            for e in entries
        ]
        metadata_path = self._backup_dir / ".metadata"
        metadata_path.write_text(
            _json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _copy_sqlite_snapshot(
        self, source_path: Path, target_path: Path
    ) -> None:
        """Copia la BD usando sqlite3.backup() para consistencia.

        A diferencia de shutil.copy2, este método genera un
        snapshot atómico de la BD incluso si hay escrituras en curso
        (compatible con WAL mode).
        """
        import sqlite3

        target_path.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(str(source_path))
        target = sqlite3.connect(str(target_path))
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
