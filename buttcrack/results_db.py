"""Tiny SQLite result ledger for resumable cryptanalysis."""
from __future__ import annotations
import json, sqlite3
from pathlib import Path

class ResultDB:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY, ciphertext_hash TEXT NOT NULL,
                attack TEXT NOT NULL, parameters TEXT NOT NULL,
                score REAL, candidate TEXT, status TEXT NOT NULL,
                runtime_seconds REAL, cpu_count INTEGER, seed INTEGER,
                verification TEXT NOT NULL, created_utc TEXT DEFAULT CURRENT_TIMESTAMP
            )""")
    def _connect(self): return sqlite3.connect(self.path)
    def add(self, *, ciphertext_hash, attack, parameters, score=None, candidate=None, status="heuristic", runtime_seconds=None, cpu_count=None, seed=None, verification="not_checked", campaign=None, chunk_id=None):
        parameters = dict(parameters or {})
        if campaign is not None: parameters["campaign"] = campaign
        if chunk_id is not None: parameters["chunk_id"] = chunk_id
        with self._connect() as db:
            db.execute("INSERT INTO results(ciphertext_hash,attack,parameters,score,candidate,status,runtime_seconds,cpu_count,seed,verification) VALUES(?,?,?,?,?,?,?,?,?,?)", (ciphertext_hash, attack, json.dumps(parameters), score, candidate, status, runtime_seconds, cpu_count, seed, verification))

    def recheck_candidate(self, candidate, *, exact_round_trip, independent, details=None):
        """Return a non-promoting audit record; callers must explicitly validate both gates."""
        return {"candidate": candidate, "exact_round_trip": bool(exact_round_trip), "independent_recheck": bool(independent), "promotable": bool(exact_round_trip and independent), "details": details or {}}

    def campaign_summary(self, campaign_id=None):
        rows=self.recent(100000)
        selected=[]
        for row in rows:
            try: params=json.loads(row[0] if False else "{}")
            except Exception: params={}
            selected.append(row)
        return {"observations": len(selected), "completed": sum(r[1]=="completed" for r in selected), "interrupted": sum(r[1]=="interrupted" for r in selected), "queued": sum(r[1]=="queued" for r in selected)}
    def leaderboard(self, limit=100, attack=None):
        """Global deduplicated view; raw observations are never overwritten."""
        query = "SELECT candidate, score, parameters, status, created_utc FROM results WHERE candidate IS NOT NULL"
        values = []
        if attack:
            query += " AND attack = ?"; values.append(attack)
        with self._connect() as db:
            rows = db.execute(query, values).fetchall()
        best = {}
        for candidate, score, parameters, status, created in rows:
            current = best.get(candidate)
            if current is None or (score is not None and (current['best_score'] is None or score > current['best_score'])):
                best[candidate] = {'candidate': candidate, 'best_score': score, 'found_in': json.loads(parameters), 'status': status, 'first_seen': created}
        return sorted(best.values(), key=lambda item: item['best_score'] if item['best_score'] is not None else float('-inf'), reverse=True)[:limit]

    def recent(self, limit=20, attack=None, status=None):
        query = "SELECT attack,status,score,candidate,verification,created_utc FROM results"
        clauses, values = [], []
        if attack: clauses.append("attack = ?"); values.append(attack)
        if status: clauses.append("status = ?"); values.append(status)
        if clauses: query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id DESC LIMIT ?"; values.append(limit)
        with self._connect() as db:
            return db.execute(query, values).fetchall()
