import json
import sqlite3
from pathlib import Path
from typing import Dict, List

from mnemos.core.models import MemoryNode, MemoryTier, SemanticEdge


class SQLiteMemoryStore:
    """Persistência transacional em SQLite com modo WAL para durabilidade e hidratação."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_nodes (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    importance REAL NOT NULL,
                    access_count INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    metadata_json TEXT NOT NULL,
                    parent_hash TEXT,
                    hmac_signature TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_edges (
                    source_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    weight REAL NOT NULL,
                    negated INTEGER NOT NULL,
                    evidence_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )

    def save_snapshot(
        self, nodes: Dict[str, MemoryNode], edges: List[SemanticEdge]
    ) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM memory_nodes")
            conn.execute("DELETE FROM semantic_edges")

            for node in nodes.values():
                conn.execute(
                    """
                    INSERT INTO memory_nodes (
                        id, content, tier, embedding_json, importance,
                        access_count, created_at, last_accessed, metadata_json,
                        parent_hash, hmac_signature
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node.id,
                        node.content,
                        node.tier.value,
                        json.dumps(node.embedding),
                        node.importance,
                        node.access_count,
                        node.created_at,
                        node.last_accessed,
                        json.dumps(node.metadata),
                        node.parent_hash,
                        node.hmac_signature,
                    ),
                )

            for edge in edges:
                conn.execute(
                    """
                    INSERT INTO semantic_edges (
                        source_id, relation, target_id, weight,
                        negated, evidence_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        edge.source_id,
                        edge.relation,
                        edge.target_id,
                        edge.weight,
                        1 if edge.negated else 0,
                        json.dumps(edge.evidence_hashes),
                        edge.updated_at,
                    ),
                )

    def load_nodes(self) -> Dict[str, MemoryNode]:
        nodes: Dict[str, MemoryNode] = {}
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM memory_nodes ORDER BY created_at ASC")
            for row in cursor.fetchall():
                node = MemoryNode(
                    id=row[0],
                    content=row[1],
                    tier=MemoryTier(row[2]),
                    embedding=json.loads(row[3]),
                    importance=row[4],
                    access_count=row[5],
                    created_at=row[6],
                    last_accessed=row[7],
                    metadata=json.loads(row[8]),
                    parent_hash=row[9],
                    hmac_signature=row[10],
                )
                nodes[node.id] = node
        return nodes

    def load_edges(self) -> List[SemanticEdge]:
        edges: List[SemanticEdge] = []
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM semantic_edges ORDER BY updated_at ASC")
            for row in cursor.fetchall():
                edges.append(
                    SemanticEdge(
                        source_id=row[0],
                        relation=row[1],
                        target_id=row[2],
                        weight=row[3],
                        negated=bool(row[4]),
                        evidence_hashes=json.loads(row[5]),
                        updated_at=row[6],
                    )
                )
        return edges
