from __future__ import annotations

from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterator


class WorkerBusy(RuntimeError):
    pass


class Store:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute('PRAGMA journal_mode=WAL')
            connection.executescript('''
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY, created_at REAL NOT NULL,
                    state TEXT NOT NULL, cancel_requested INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL, at REAL NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, sequence);
                CREATE TABLE IF NOT EXISTS campaigns (
                    campaign_id TEXT PRIMARY KEY, created_at REAL NOT NULL,
                    state TEXT NOT NULL, cancel_requested INTEGER NOT NULL DEFAULT 0
                );
            ''')

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.root / 'harness.sqlite3', timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA busy_timeout=10000')
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @contextmanager
    def _file_lock(self, lock_name: str, message: str) -> Iterator[None]:
        with (self.root / f'{lock_name}.lock').open('a') as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise WorkerBusy(message) from error
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    @contextmanager
    def worker_lock(self, run_id: str) -> Iterator[None]:
        self.load(run_id)
        with self._file_lock(run_id, 'A worker is already advancing this run'):
            yield

    @contextmanager
    def campaign_lock(self, campaign_id: str) -> Iterator[None]:
        self.load_campaign(campaign_id)
        with self._file_lock(campaign_id, 'A worker is already advancing this campaign'):
            yield

    def create(self, state: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute('INSERT INTO runs(run_id, created_at, state) VALUES (?, ?, ?)',
                               (state['run_id'], state['created_at'], json.dumps(state, ensure_ascii=False)))

    def load(self, run_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            if run_id == 'latest':
                row = connection.execute('SELECT * FROM runs ORDER BY created_at DESC, rowid DESC LIMIT 1').fetchone()
            else:
                row = connection.execute('SELECT * FROM runs WHERE run_id = ?', (run_id,)).fetchone()
        if row is None:
            raise ValueError(f'Unknown run: {run_id}')
        return json.loads(row['state'])

    def save(self, state: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute('UPDATE runs SET state = ? WHERE run_id = ?',
                               (json.dumps(state, ensure_ascii=False), state['run_id']))

    def request_stop(self, run_id: str) -> None:
        with self.connect() as connection:
            connection.execute('UPDATE runs SET cancel_requested = 1 WHERE run_id = ?', (run_id,))

    def cancel_requested(self, run_id: str) -> bool:
        with self.connect() as connection:
            row = connection.execute('SELECT cancel_requested FROM runs WHERE run_id = ?', (run_id,)).fetchone()
        return bool(row['cancel_requested'])

    def create_campaign(self, state: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute('INSERT INTO campaigns(campaign_id, created_at, state) VALUES (?, ?, ?)',
                               (state['campaign_id'], state['created_at'], json.dumps(state, ensure_ascii=False)))

    def load_campaign(self, campaign_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            if campaign_id == 'latest':
                row = connection.execute(
                    'SELECT * FROM campaigns ORDER BY created_at DESC, rowid DESC LIMIT 1'
                ).fetchone()
            else:
                row = connection.execute('SELECT * FROM campaigns WHERE campaign_id = ?', (campaign_id,)).fetchone()
        if row is None:
            raise ValueError(f'Unknown campaign: {campaign_id}')
        return json.loads(row['state'])

    def save_campaign(self, state: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute('UPDATE campaigns SET state = ? WHERE campaign_id = ?',
                               (json.dumps(state, ensure_ascii=False), state['campaign_id']))

    def request_campaign_stop(self, campaign_id: str) -> None:
        with self.connect() as connection:
            connection.execute('UPDATE campaigns SET cancel_requested = 1 WHERE campaign_id = ?', (campaign_id,))

    def campaign_cancel_requested(self, campaign_id: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                'SELECT cancel_requested FROM campaigns WHERE campaign_id = ?', (campaign_id,)
            ).fetchone()
        return bool(row['cancel_requested'])

    def event(self, run_id: str, kind: str, data: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute('INSERT INTO events(run_id, at, kind, data) VALUES (?, ?, ?, ?)',
                               (run_id, time.time(), kind, json.dumps(data, ensure_ascii=False)))

    def events(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute('SELECT * FROM events WHERE run_id = ? ORDER BY sequence', (run_id,)).fetchall()
        return [{**dict(row), 'data': json.loads(row['data'])} for row in rows]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(content, encoding='utf-8')
    temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')
