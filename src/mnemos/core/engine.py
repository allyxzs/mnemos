import asyncio
import hashlib
import math
import time
import uuid
from collections import Counter
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


def tokenize(text: str) -> List[str]:
    cleaned = "".join(c.lower() if c.isalnum() else " " for c in text)
    return [t for t in cleaned.split() if len(t) > 1]


class MnemosEngineV2:
    """
    Orquestrador Cognitivo Mnemos v2.5:
    - Camadas L1 (Working), L2 (Episodic Ebbinghaus), L3 (Semantic Knowledge Graph)
    - Quad-Fusion Recall (Vector + Okapi BM25 + Ebbinghaus + Graph Spreading Activation)
    - Auditoria Merkle-DAG + HMAC-SHA256 com Auto-Cura (Self-Healing)
    - Persistência e Hidratação Transacional SQLite WAL
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

        if self.store:
            self._hydrate_from_store()

    def _hydrate_from_store(self) -> None:
        if not self.store:
            return
        loaded_nodes = self.store.load_nodes()
        loaded_edges = self.store.load_edges()
        for node in loaded_nodes.values():
            self._nodes[node.id] = node
            if node.tier == MemoryTier.WORKING:
                self._working_queue.append(node.id)
            if node.parent_hash and node.hmac_signature:
                h = node.content_hash
                self.ledger._chain.append(h)
                self.ledger._snapshots[h] = node.model_copy(deep=True)

        for edge in loaded_edges:
            self.graph.adj[edge.source_id].append(edge)
            self.graph.reverse_adj[edge.target_id].append(edge)

    @staticmethod
    def _deterministic_ngram_embedding(text: str, dim: int = 64) -> List[float]:
        vec = [0.0] * dim
        tokens = tokenize(text)
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

    def _compute_bm25_scores(
        self, query_tokens: List[str], k1: float = 1.5, b: float = 0.75
    ) -> Dict[str, float]:
        if not query_tokens or not self._nodes:
            return {}

        doc_tokens: Dict[str, List[str]] = {
            nid: tokenize(node.content) for nid, node in self._nodes.items()
        }
        total_docs = len(doc_tokens)
        avgdl = sum(len(t) for t in doc_tokens.values()) / max(1, total_docs)

        df: Counter[str] = Counter()
        for tokens in doc_tokens.values():
            for term in set(tokens):
                df[term] += 1

        raw_scores: Dict[str, float] = {}
        for nid, tokens in doc_tokens.items():
            tf = Counter(tokens)
            doc_len = len(tokens)
            score = 0.0
            for q_term in query_tokens:
                if q_term not in tf:
                    continue
                n_q = df[q_term]
                idf = math.log(((total_docs - n_q + 0.5) / (n_q + 0.5)) + 1.0)
                freq = tf[q_term]
                denom = freq + k1 * (1.0 - b + b * (doc_len / max(1.0, avgdl)))
                score += idf * ((freq * (k1 + 1.0)) / denom)
            raw_scores[nid] = score

        max_score = max(raw_scores.values(), default=0.0)
        if max_score <= 0.0:
            return {nid: 0.0 for nid in self._nodes}
        return {nid: s / max_score for nid, s in raw_scores.items()}

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
        alpha_vector: float = 0.40,
        delta_bm25: float = 0.20,
        beta_retention: float = 0.20,
        gamma_graph: float = 0.20,
    ) -> List[Tuple[MemoryNode, float]]:
        query_vec = self.embed(query)
        query_tokens = tokenize(query)
        now = time.time()

        graph_boosts: Dict[str, float] = {}
        if seed_entities:
            graph_boosts = self.graph.spreading_activation(seed_entities)

        scored_results: List[Tuple[MemoryNode, float]] = []

        async with self._lock:
            if not self.ledger.verify_integrity(self._nodes):
                self.ledger.heal_live_state(self._nodes)

            bm25_scores = self._compute_bm25_scores(query_tokens)

            for node in self._nodes.values():
                sim = max(0.0, cosine_similarity(query_vec, node.embedding))
                bm25 = bm25_scores.get(node.id, 0.0)
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
                    + (delta_bm25 * bm25)
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

    async def verify_and_heal(self) -> Dict[str, Any]:
        async with self._lock:
            intact_before = self.ledger.verify_integrity(self._nodes)
            healed_count, healed_ids = self.ledger.heal_live_state(self._nodes)
            intact_after = self.ledger.verify_integrity(self._nodes)
            return {
                "intact_before_healing": intact_before,
                "healed_nodes_count": healed_count,
                "healed_node_ids": healed_ids,
                "intact_after_healing": intact_after,
                "state_root": self.ledger.compute_state_root(),
            }

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

            if self.store:
                all_edges = [e for edges in self.graph.adj.values() for e in edges]
                self.store.save_snapshot(self._nodes, all_edges)

            return {
                "pruned_nodes": pruned_count,
                "merged_nodes": merged_count,
                "active_nodes": len(self._nodes),
                "dialectical_conflicts": len(self.graph.conflicts),
                "ledger_verified": self.ledger.verify_integrity(self._nodes),
                "state_root": self.ledger.compute_state_root(),
            }
