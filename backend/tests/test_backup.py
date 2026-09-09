"""Real SQLite/WAL recovery checks; all data and processes stay in temporary paths."""
import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from atlas_quant import backup
from atlas_quant.backup import BackupError, create_backup, prune_backups, restore_backup, validate_backup
from atlas_quant.store import Store
from atlas_quant.worker_lock import WorkerLock


class Lock:
    def __init__(self, available=True):
        self.available = available
        self.held = False
        self.released = False

    def acquire(self):
        self.held = self.available
        return self.held

    def release(self):
        self.held = False
        self.released = True


def database(tmp_path, name="source"):
    store = Store(tmp_path / name / "atlas.sqlite3")
    store.put("note", {"id": "metadata", "text": "retained"})
    store.put("ledger", {"id": "portfolio", "events": [{"id": "deposit", "date": "2026-01-01", "kind": "deposit", "amount": 123}]}, "ledger.saved")
    return store


def contents(path):
    with closing(sqlite3.connect(path)) as db:
        return db.execute("SELECT kind,id,body FROM records ORDER BY kind,id").fetchall()


def manifest_for(folder):
    return json.loads((folder / "manifest.json").read_text(encoding="utf-8"))


def rewrite_manifest(folder, **changes):
    manifest = {**manifest_for(folder), **changes}
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_backup_includes_committed_wal_and_excludes_uncommitted_writes(tmp_path):
    store = database(tmp_path)
    with closing(sqlite3.connect(store.path)) as writer, writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("INSERT INTO records VALUES('ledger','committed','{\"id\":\"committed\"}')")
        writer.commit()
        assert Path(str(store.path) + "-wal").stat().st_size > 0
        writer.execute("INSERT INTO records VALUES('ledger','pending','{\"id\":\"pending\"}')")
        folder = create_backup(store.path, tmp_path / "backups")
        copied = contents(folder / "atlas.sqlite3")
        assert any(row[1] == "committed" for row in copied)
        assert not any(row[1] == "pending" for row in copied)
        writer.rollback()
    manifest = validate_backup(folder)
    assert {k: manifest["schema"]["tables"][k] for k in ("records", "audit", "versions")} == {"records": 2, "audit": 1, "versions": 0}
    assert manifest["schema"]["tables"]["ledger_entries"] == 1
    assert manifest["sha256"] == hashlib.sha256((folder / "atlas.sqlite3").read_bytes()).hexdigest()
    assert set(p.name for p in folder.iterdir()) == {"atlas.sqlite3", "manifest.json"}


def test_missing_database_does_not_create_empty_source(tmp_path):
    with pytest.raises(BackupError, match="No existe"):
        create_backup(tmp_path / "missing.sqlite3", tmp_path / "backups")
    assert not (tmp_path / "missing.sqlite3").exists()


def test_backup_does_not_copy_environment_or_credentials(tmp_path, monkeypatch):
    store = database(tmp_path)
    secret = "test-only-sentinel-not-a-real-key"
    (store.path.parent / ".env").write_text("OPENAI_API_KEY=" + secret)
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    folder = create_backup(store.path, tmp_path / "backups")
    assert all(secret.encode() not in file.read_bytes() for file in folder.iterdir())


def test_failed_publication_leaves_no_visible_partial_backup(tmp_path, monkeypatch):
    store = database(tmp_path)
    before = contents(store.path)

    def fail(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(backup.os, "replace", fail)
    with pytest.raises(BackupError, match="publicar"):
        create_backup(store.path, tmp_path / "backups")
    assert list((tmp_path / "backups").iterdir()) == []
    assert contents(store.path) == before


@pytest.mark.parametrize("schema_version", [0, 1, 2, 3])
def test_current_and_legacy_schema_backups_are_supported(tmp_path, schema_version):
    store = database(tmp_path)
    with closing(sqlite3.connect(store.path)) as db, db:
        if schema_version < 3:
            from atlas_quant.book_store import DDL as BOOK_DDL
            for table in reversed(BOOK_DDL):
                db.execute(f"DROP TABLE {table}")
        if schema_version < 2:
            from atlas_quant.identity_store import DDL
            for table in reversed(DDL):
                db.execute(f"DROP TABLE {table}")
        db.execute(f"PRAGMA user_version={schema_version}")
    folder = create_backup(store.path, tmp_path / "backups")
    assert validate_backup(folder)["schema"]["user_version"] == schema_version


@pytest.mark.parametrize("damage", ["bytes", "hash", "future_app", "timestamp", "schema_counts", "extra_file"])
def test_invalid_backup_never_overwrites_destination(tmp_path, damage):
    source = database(tmp_path)
    target = database(tmp_path, "target")
    target.put("ledger", {"id": "unique-to-target", "events": []})
    original = contents(target.path)
    folder = create_backup(source.path, tmp_path / "backups")
    if damage == "bytes":
        with (folder / "atlas.sqlite3").open("ab") as stream:
            stream.write(b"corruption")
    elif damage == "hash":
        rewrite_manifest(folder, sha256="0" * 64)
    elif damage == "future_app":
        rewrite_manifest(folder, app_version="999.0.0")
    elif damage == "timestamp":
        rewrite_manifest(folder, created_at="invalid")
    elif damage == "schema_counts":
        rewrite_manifest(folder, schema={"user_version": 0, "tables": {}})
    else:
        (folder / "atlas.sqlite3-wal").write_bytes(b"unverified WAL")
    lock = Lock()
    with pytest.raises(BackupError):
        restore_backup(folder, target.path, tmp_path / "before", instance_lock=lock)
    assert contents(target.path) == original
    assert lock.released
    assert not (tmp_path / "before").exists()


@pytest.mark.parametrize("mutation", ["future_schema", "wrong_table", "invalid_json", "trigger"])
def test_sqlite_validation_rejects_incompatible_state_before_publication(tmp_path, mutation):
    store = database(tmp_path)
    with closing(sqlite3.connect(store.path)) as db, db:
        if mutation == "future_schema":
            db.execute("PRAGMA user_version=99")
        elif mutation == "wrong_table":
            db.execute("CREATE TABLE unrelated(x TEXT)")
        elif mutation == "invalid_json":
            db.execute("UPDATE records SET body='not json'")
        else:
            db.execute("CREATE TRIGGER unwanted AFTER INSERT ON records BEGIN DELETE FROM audit; END")
    with pytest.raises(BackupError):
        create_backup(store.path, tmp_path / "backups")
    assert list((tmp_path / "backups").iterdir()) == []


def test_restore_preserves_previous_database_and_disables_automatic_activity(tmp_path):
    source = database(tmp_path)
    statuses = ["queued", "running", "observing", "eligible_paper", "paper", "paused", "completed"]
    for status in statuses:
        source.put("experiment", {"id": status, "status": status, "auto_paper": True,
                   "provider": "openai", "budget_usd": 5, "spent_usd": 1, "reserved_usd": 2,
                   "paper_account": {"enabled": True, "cash": 321, "positions": {"DEMO": 2},
                                     "orders": [{"id": "pending", "status": "pending"},
                                                {"id": "filled", "status": "filled"}]}})
    source.put("settings", {"id": "main", "kill_switch": False, "max_position_weight": 0.1})
    source.put("dataset", {"id": "feed", "feed": {"symbol": "DEMO", "last_attempt": "2026-01-01"}})
    folder = create_backup(source.path, tmp_path / "backups")
    source_before = contents(folder / "atlas.sqlite3")
    target = database(tmp_path, "target")
    target.put("ledger", {"id": "destination-only", "events": []})
    previous_contents = contents(target.path)
    lock = Lock()
    result = restore_backup(folder, target.path, tmp_path / "backups", instance_lock=lock)
    assert lock.released
    assert contents(Path(result["pre_restore_backup"]) / "atlas.sqlite3") == previous_contents
    validate_backup(result["pre_restore_backup"])
    assert contents(folder / "atlas.sqlite3") == source_before
    restored = Store(target.path)
    for status in statuses:
        job = restored.get("experiment", status)
        assert job["status"] == ("completed" if status == "completed" else "paused")
        if job["status"] == "paused":
            assert job["resume_status"] == "interrupted"
        assert job["reserved_usd"] == 2 and job["spent_usd"] == 1 and job["budget_usd"] == 5
        assert job["auto_paper"] is False
        assert job["paper_account"]["enabled"] is False
        assert job["paper_account"]["cash"] == 321
        assert job["paper_account"]["positions"] == {"DEMO": 2}
        assert [order["status"] for order in job["paper_account"]["orders"]] == ["cancelled", "filled"]
    assert restored.get("settings", "main")["kill_switch"] is True
    assert restored.get("settings", "main")["max_position_weight"] == 0.1
    feed = restored.get("dataset", "feed")
    assert "feed" not in feed and feed["restored_feed"]["symbol"] == "DEMO"
    assert restored.audit_list(1)[0]["event"] == "database.restored"
    assert result["paused_experiments"] == 5 and result["disabled_feeds"] == 1


def test_running_installation_lock_blocks_restore_before_writes(tmp_path):
    source = database(tmp_path)
    folder = create_backup(source.path, tmp_path / "backups")
    missing_target = tmp_path / "target" / "atlas.sqlite3"
    with pytest.raises(BackupError, match="ejecución"):
        restore_backup(folder, missing_target, tmp_path / "before", instance_lock=Lock(False))
    assert not missing_target.parent.exists()


def test_real_instance_lock_blocks_restore(tmp_path):
    from tools.atlas_runtime import InstanceLock

    source = database(tmp_path)
    folder = create_backup(source.path, tmp_path / "backups")
    lock_path = tmp_path / "var" / "atlas.lock"
    held = InstanceLock(lock_path)
    assert held.acquire()
    try:
        with pytest.raises(BackupError, match="ejecución"):
            restore_backup(folder, tmp_path / "target.sqlite3", tmp_path / "before",
                           instance_lock=InstanceLock(lock_path))
    finally:
        held.release()
    result = restore_backup(folder, tmp_path / "target.sqlite3", tmp_path / "before",
                            instance_lock=InstanceLock(lock_path))
    assert Path(result["target"]).exists()


@pytest.mark.parametrize("suffix", [".worker.lock", ".tick.lock"])
def test_direct_executor_lock_blocks_restore_before_database_or_backup_write(tmp_path, suffix):
    source = database(tmp_path)
    target = database(tmp_path, "target")
    target.put("ledger", {"id": "target-only", "events": []})
    folder = create_backup(source.path, tmp_path / "backups")
    before = contents(target.path)
    installation = Lock()
    with WorkerLock(str(target.path) + suffix):
        with pytest.raises(BackupError, match="ejecutor"):
            restore_backup(folder, target.path, tmp_path / "before", instance_lock=installation)
    assert contents(target.path) == before
    assert not (tmp_path / "before").exists()
    assert list(target.path.parent.glob(".atlas-restore-*")) == []
    assert installation.released
    # A refused restore must release any lock it acquired before contention.
    result = restore_backup(folder, target.path, tmp_path / "before", instance_lock=Lock())
    assert Path(result["target"]).exists()


def test_restore_clears_old_execution_ownership_and_preserves_safe_resume(tmp_path):
    from atlas_quant.controls import control_experiment

    source = database(tmp_path)
    source.put("experiment", {"id": "observation", "status": "observing", "execution_active": True,
        "execution_token": "old-owner", "control_requested": None, "reserved_usd": 0,
        "spent_usd": 0, "auto_paper": True, "paper_account": None})
    source.put("dataset", {"id": "feed", "feed": {"symbol": "ETF", "request_id": "old-download"}})
    folder = create_backup(source.path, tmp_path / "backups")
    target = tmp_path / "target" / "atlas.sqlite3"
    restore_backup(folder, target, tmp_path / "before", instance_lock=Lock())
    restored = Store(target)
    restored.recover()
    paused = restored.get("experiment", "observation")
    assert paused["status"] == "paused"
    assert paused["resume_status"] == "observing"
    assert paused["execution_active"] is False
    assert paused["control_requested"] is None
    assert "execution_token" not in paused
    assert "request_id" not in restored.get("dataset", "feed")["restored_feed"]
    resumed = control_experiment(restored, "observation", "resume")
    assert resumed["status"] == "observing"
    assert resumed["auto_paper"] is False
    assert restored.get("settings", "main")["kill_switch"] is True


@pytest.mark.parametrize("status,resume_status,reserved", [
    ("paused", "running", 0), ("running", None, 0),
    ("paused", "running", 1), ("observing", None, 1),
])
def test_restore_in_flight_work_never_replays_api(tmp_path, status, resume_status, reserved):
    from atlas_quant.controls import control_experiment

    source = database(tmp_path)
    source.put("experiment", {"id": "job", "status": status, "resume_status": resume_status,
        "execution_active": True, "execution_token": "old-owner", "control_requested": "pause",
        "reserved_usd": reserved, "spent_usd": 0.25, "auto_paper": False, "paper_account": None})
    folder = create_backup(source.path, tmp_path / "backups")
    target = tmp_path / "target" / "atlas.sqlite3"
    restore_backup(folder, target, tmp_path / "before", instance_lock=Lock())
    restored = Store(target)
    restored.recover()
    job = restored.get("experiment", "job")
    assert job["status"] == "paused"
    assert job["resume_status"] == "interrupted"
    assert job["reserved_usd"] == reserved
    assert job["spent_usd"] == 0.25
    assert job["execution_active"] is False
    assert "execution_token" not in job
    if reserved:
        with pytest.raises(ValueError, match="reserva"):
            control_experiment(restored, "job", "resume")
    else:
        assert control_experiment(restored, "job", "resume")["status"] == "interrupted"


def test_failed_restore_publication_preserves_original_and_pre_restore_backup(tmp_path, monkeypatch):
    source = database(tmp_path)
    target = database(tmp_path, "target")
    target.put("ledger", {"id": "target-only", "events": []})
    previous = contents(target.path)
    folder = create_backup(source.path, tmp_path / "backups")
    original_replace = backup.os.replace

    def fail_target(source_path, target_path):
        if Path(target_path) == target.path:
            raise OSError("simulated destination replacement failure")
        original_replace(source_path, target_path)

    monkeypatch.setattr(backup.os, "replace", fail_target)
    with pytest.raises(BackupError, match="Copia previa conservada"):
        restore_backup(folder, target.path, tmp_path / "before", instance_lock=Lock())
    assert contents(target.path) == previous
    pre_restore = list((tmp_path / "before").iterdir())
    assert len(pre_restore) == 1
    assert contents(pre_restore[0] / "atlas.sqlite3") == previous
    assert list(target.path.parent.glob(".atlas-restore-*")) == []


def test_backup_changed_during_restore_is_rejected_before_touching_target(tmp_path, monkeypatch):
    source = database(tmp_path)
    target = database(tmp_path, "target")
    before = contents(target.path)
    folder = create_backup(source.path, tmp_path / "backups")
    original_copy = backup.shutil.copyfile

    def tamper_during_copy(source_path, target_path):
        original_copy(source_path, target_path)
        with Path(target_path).open("ab") as stream:
            stream.write(b"changed")

    monkeypatch.setattr(backup.shutil, "copyfile", tamper_during_copy)
    with pytest.raises(BackupError, match="cambió"):
        restore_backup(folder, target.path, tmp_path / "before", instance_lock=Lock())
    assert contents(target.path) == before
    assert not (tmp_path / "before").exists()


def test_orphaned_wal_is_preserved_and_blocks_restore_to_missing_database(tmp_path):
    source = database(tmp_path)
    folder = create_backup(source.path, tmp_path / "backups")
    target = tmp_path / "target.sqlite3"
    orphan = Path(str(target) + "-wal")
    orphan.write_bytes(b"pending original data")
    with pytest.raises(BackupError, match="pendientes"):
        restore_backup(folder, target, tmp_path / "before", instance_lock=Lock())
    assert not target.exists()
    assert orphan.read_bytes() == b"pending original data"


def test_open_destination_connection_blocks_replacement_and_preserves_wal(tmp_path):
    source = database(tmp_path)
    target = database(tmp_path, "target")
    folder = create_backup(source.path, tmp_path / "backups")
    with closing(sqlite3.connect(target.path)) as active:
        active.execute("PRAGMA journal_mode=WAL")
        active.execute("BEGIN")
        active.execute("SELECT * FROM records").fetchall()
        previous = contents(target.path)
        with pytest.raises(BackupError):
            restore_backup(folder, target.path, tmp_path / "before", instance_lock=Lock())
        assert contents(target.path) == previous
    assert len(list((tmp_path / "before").iterdir())) == 1


def test_pruning_retains_newest_verified_backups_by_manifest_date(tmp_path):
    source = database(tmp_path)
    directory = tmp_path / "automatic"
    folders = [create_backup(source.path, directory) for _ in range(4)]
    # Directory names and filesystem modification times are not the authority.
    for folder, day in zip(folders, [3, 1, 4, 2], strict=True):
        rewrite_manifest(folder, created_at=f"2026-01-{day:02d}T00:00:00+00:00")
    removed = prune_backups(directory, keep=2)
    assert removed == [folders[1], folders[3]]
    assert set(directory.iterdir()) == {folders[0], folders[2]}
    assert all(validate_backup(folder) for folder in directory.iterdir())
    assert prune_backups(directory, keep=2) == []


def test_pruning_ignores_foreign_malformed_and_linked_folders(tmp_path):
    source = database(tmp_path)
    directory = tmp_path / "automatic"
    oldest = create_backup(source.path, directory)
    newest = create_backup(source.path, directory)
    rewrite_manifest(oldest, created_at="2026-01-01T00:00:00+00:00")
    rewrite_manifest(newest, created_at="2026-01-02T00:00:00+00:00")
    foreign = directory / "personal-folder"
    foreign.mkdir()
    (foreign / "important.txt").write_text("keep this")
    malformed = directory / "atlas-20260101T000000000000Z-aaaaaaaa"
    malformed.mkdir()
    (malformed / "manifest.json").write_text("not JSON")
    external = create_backup(source.path, tmp_path / "elsewhere")
    link = directory / "atlas-20260101T000000000000Z-bbbbbbbb"
    try:
        link.symlink_to(external, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        # Windows junctions do not require the administrator privilege that
        # symlinks may require. Both must be excluded by the production guard.
        import _winapi
        _winapi.CreateJunction(str(external), str(link))
    assert link.is_symlink() or link.is_junction()
    assert prune_backups(directory, keep=1) == [oldest]
    assert validate_backup(newest)
    assert validate_backup(external)
    assert (foreign / "important.txt").read_text() == "keep this"
    assert (malformed / "manifest.json").read_text() == "not JSON"
    assert link.exists()


@pytest.mark.parametrize("keep", [0, -1, True, 1.5])
def test_pruning_rejects_invalid_keep_without_deleting(tmp_path, keep):
    source = database(tmp_path)
    folder = create_backup(source.path, tmp_path / "automatic")
    with pytest.raises(BackupError, match="al menos una"):
        prune_backups(folder.parent, keep=keep)
    assert validate_backup(folder)


def test_pruning_malformed_root_or_insufficient_valid_copies_deletes_nothing(tmp_path):
    wrong_root = tmp_path / "not-a-directory"
    wrong_root.write_text("unchanged")
    with pytest.raises(BackupError, match="directorio"):
        prune_backups(wrong_root)
    assert wrong_root.read_text() == "unchanged"
    source = database(tmp_path)
    first = create_backup(source.path, tmp_path / "automatic")
    bad = create_backup(source.path, tmp_path / "automatic")
    rewrite_manifest(bad, sha256="0" * 64)
    assert prune_backups(first.parent, keep=1) == []
    assert first.exists() and bad.exists()


def test_pruning_stops_if_survivor_changes_after_inventory(tmp_path, monkeypatch):
    source = database(tmp_path)
    directory = tmp_path / "automatic"
    old = create_backup(source.path, directory)
    recent = create_backup(source.path, directory)
    rewrite_manifest(old, created_at="2026-01-01T00:00:00+00:00")
    rewrite_manifest(recent, created_at="2026-01-02T00:00:00+00:00")
    original_validate = backup.validate_backup
    calls = 0

    def change_survivor(folder):
        nonlocal calls
        calls += 1
        if calls == 3:
            rewrite_manifest(recent, sha256="0" * 64)
        return original_validate(folder)

    monkeypatch.setattr(backup, "validate_backup", change_survivor)
    with pytest.raises(BackupError):
        prune_backups(directory, keep=1)
    assert old.exists() and recent.exists()


def test_pruning_failure_preserves_the_retained_backup(tmp_path, monkeypatch):
    source = database(tmp_path)
    directory = tmp_path / "automatic"
    old = create_backup(source.path, directory)
    recent = create_backup(source.path, directory)
    rewrite_manifest(old, created_at="2026-01-01T00:00:00+00:00")
    rewrite_manifest(recent, created_at="2026-01-02T00:00:00+00:00")

    def denied(folder):
        raise PermissionError("simulated retention failure")

    monkeypatch.setattr(backup.shutil, "rmtree", denied)
    with pytest.raises(BackupError, match="retención"):
        prune_backups(directory, keep=1)
    assert validate_backup(recent)
    assert old.exists()
