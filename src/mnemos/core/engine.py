import asyncio
import hashlib
import math
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from mnemos.core.ledger import MerkleMemoryLedger
from mnemos.core.models import MemoryNode, MemoryTier
from mnemos.memory.semantic_graph import SemanticKnowledgeGraph
from mnemos.security.sanitizer import CognitiveSanitizer
from mnemos.storage.sqlite_store import SQLiteMemoryStore


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class MnemosEngineV2:
    """
    Orquestrador Cognitivo Mnemos v2.0:
    - Camadas L1 (Working), L2 (Episodic Ebbinghaus), L3 (Semantic Knowledge Graph)
    - Auditoria Merkle-DAG + HMAC-SHA256
    - Defesa ativa contra Memory Poisoning
    - Persistência SQLite WAL
    """

    def __init__(
        self,
        embedding_fn: Optional[Callable[[str], List[float]]] = None,
        working_memory_limit: int = 12,
        secret_key: str = "mnemos-v2-sovereign-secret",
        db_path: Optional[str | Path] = None,
    ) -> None:
        self.working_limit = working_memory_limit
        self.embed = embedding_fn or self._deterministic_ngram_embedding
        self.ledger = MerkleMemoryLedger(secret_key=secret_key)
        self.graph = SemanticKnowledgeGraph()
        self.store = SQLiteMemoryStore(db_path) if db_path else None
        self._nodes: Dict[str, MemoryNode] = {}
        self._working_queue: List[str] = []
        self._lock = asyncio.Lock()

    @staticmethod
    def _deterministic_ngram_embedding(text: str, dim: int = 64) -> List[float]:
        """Embedding determinístico baseado em n-gramas e palavras para execução zero-dependência."""
        vec = [0.0] * dim
        cleaned = "".join(c.lower() if c.isalnum() else " " for c in text)
        tokens = cleaned.split()
        features = list(tokens)
        for token in tokens:
            if len(token) >= 4:
                features.extend(token[i : i + 3] for i in range(len(token) - 2))

        for feat in features:
            h = hashlib.sha256(feat.encode("utf-8")).digest()
            for i in range(dim):
                vec[i] += (h[i % len(h)] - 128.0) / 128.0

        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 6) for x in vec]

    async def remember(
        self,
        content: str,
        importance: float = 0.6,
        triplets: Optional[List[Tuple[str, str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryNode:
        clean_content = CognitiveSanitizer.validate(content)

        async with self._lock:
            node_id = f"mem_{uuid.uuid4().hex[:12]}"
            embedding = self.embed(clean_content)

            node = MemoryNode(
                id=node_id,
                content=clean_content,
                tier=MemoryTier.WORKING,
                embedding=embedding,
                importance=importance,
                metadata=metadata or {},
            )

            tx_hash = self.ledger.append(node)
            self._nodes[node_id] = node
            self._working_queue.append(node_id)

            if triplets:
                for subj, rel, obj in triplets:
                    self.graph.upsert_edge(
                        subj, rel, obj, evidence_hash=tx_hash, weight=importance + 0.5
                    )

            if len(self._working_queue) > self.working_limit:
                evicted_id = self._working_queue.pop(0)
                if evicted_id in self._nodes:
                    self._nodes[evicted_id].tier = MemoryTier.EPISODIC

            if self.store:
                all_edges = [e for edges in self.graph.adj.values() for e in edges]
                self.store.save_snapshot(self._nodes, all_edges)

            return node

    async def recall(
        self,
        query: str,
        top_k: int = 5,
        seed_entities: Optional[List[str]] = None,
        alpha_vector: float = 0.55,
        beta_retention: float = 0.25,
        gamma_graph: float = 0.20,
    ) -> List[Tuple[MemoryNode, float]]:
        query_vec = self.embed(query)
        now = time.time()

        graph_boosts: Dict[str, float] = {}
        if seed_entities:
            graph_boosts = self.graph.spreading_activation(seed_entities)

        scored_results: List[Tuple[MemoryNode, float]] = []

        async with self._lock:
            for node in self._nodes.values():
                sim = max(0.0, cosine_similarity(query_vec, node.embedding))
                retention = node.retention_score(current_time=now)

                g_score = 0.0
                if graph_boosts:
                    content_lower = node.content.lower()
                    matched_energies = [
                        energy
                        for entity, energy in graph_boosts.items()
                        if entity in content_lower
                    ]
                    if matched_energies:
                        g_score = min(1.0, sum(matched_energies) / len(matched_energies))

                final_score = (
                    (alpha_vector * sim)
                    + (beta_retention * retention)
                    + (gamma_graph * g_score)
                )
                scored_results.append((node, round(final_score, 4)))

            scored_results.sort(key=lambda x: x[1], reverse=True)
            top_matches = scored_results[:top_k]

            for node, _ in top_matches:
                node.access_count += 1
                node.last_accessed = now
                if node.access_count >= 4 and node.importance >= 0.75:
                    node.tier = MemoryTier.SEMANTIC

            return top_matches

    async def consolidate_and_prune(
        self,
        min_retention_threshold: float = 0.15,
        similarity_merge_threshold: float = 0.90,
        simulated_now: Optional[float] = None,
    ) -> Dict[str, Any]:
        now = simulated_now or time.time()
        pruned_count = 0
        merged_count = 0

        async with self._lock:
            node_ids = list(self._nodes.keys())
            to_delete = set()

            for nid in node_ids:
                node = self._nodes[nid]
                if node.tier == MemoryTier.EPISODIC and node.importance < 0.45:
                    if node.retention_score(now) < min_retention_threshold:
                        to_delete.add(nid)
                        pruned_count += 1

            surviving_ids = [nid for nid in node_ids if nid not in to_delete]
            for i in range(len(surviving_ids)):
                id_a = surviving_ids[i]
                if id_a in to_delete:
                    continue
                node_a = self._nodes[id_a]

                for j in range(i + 1, len(surviving_ids)):
                    id_b = surviving_ids[j]
                    if id_b in to_delete:
                        continue
                    node_b = self._nodes[id_b]

                    if (
                        cosine_similarity(node_a.embedding, node_b.embedding)
                        >= similarity_merge_threshold
                    ):
                        node_a.access_count += node_b.access_count
                        node_a.importance = min(
                            1.0, max(node_a.importance, node_b.importance) + 0.05
                        )
                        to_delete.add(id_b)
                        merged_count += 1

            for nid in to_delete:
                self._nodes.pop(nid, None)
                if nid in self._working_queue:
                    self._working_queue.remove(nid)

            return {
                "pruned_nodes": pruned_count,
                "merged_nodes": merged_count,
                "active_nodes": len(self._nodes),
                "dialectical_conflicts": len(self.graph.conflicts),
                "ledger_verified": self.ledger.verify_integrity(),
                "state_root": self.ledger.compute_state_root(),
            }
