from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple
from mnemos.core.models import ConflictRecord, SemanticEdge


class SemanticKnowledgeGraph:
    """
    Camada L3: Grafo Dirigido de Relações Conceituais com Spreading Activation
    e Detecção Dialética de Conflitos Factuais.
    """

    FUNCTIONAL_RELATIONS = {
        "RODA_SO",
        "USA_FIREWALL",
        "TEM_STATUS",
        "LOCALIZADO_EM",
        "VERSAO_ATUAL",
        "PORTA_PADRAO",
    }

    def __init__(self) -> None:
        self.adj: Dict[str, List[SemanticEdge]] = defaultdict(list)
        self.reverse_adj: Dict[str, List[SemanticEdge]] = defaultdict(list)
        self.conflicts: List[ConflictRecord] = []

    def upsert_edge(
        self,
        source: str,
        relation: str,
        target: str,
        evidence_hash: str,
        weight: float = 1.0,
        negated: bool = False,
    ) -> Optional[ConflictRecord]:
        src = source.strip().lower()
        rel = relation.strip().upper()
        tgt = target.strip().lower()

        conflict_detected: Optional[ConflictRecord] = None

        # Verifica atualização ou contradição dialética em relações funcionais (1:1)
        for edge in list(self.adj[src]):
            if edge.relation == rel:
                if edge.target_id == tgt and edge.negated == negated:
                    edge.weight = min(5.0, edge.weight + (weight * 0.25))
                    if evidence_hash not in edge.evidence_hashes:
                        edge.evidence_hashes.append(evidence_hash)
                    return None

                if rel in self.FUNCTIONAL_RELATIONS or edge.target_id == tgt:
                    conflict_detected = ConflictRecord(
                        subject=src,
                        relation=rel,
                        existing_target=edge.target_id,
                        conflicting_target=tgt,
                        resolution="SUPERSEDED_BY_NEWER_EVIDENCE",
                    )
                    self.conflicts.append(conflict_detected)
                    # Atenua peso da memória antiga superada
                    edge.weight = max(0.1, edge.weight * 0.4)

        new_edge = SemanticEdge(
            source_id=src,
            target_id=tgt,
            relation=rel,
            weight=weight,
            negated=negated,
            evidence_hashes=[evidence_hash],
        )
        self.adj[src].append(new_edge)
        self.reverse_adj[tgt].append(new_edge)
        return conflict_detected

    def spreading_activation(
        self, seed_entities: List[str], depth: int = 2, decay: float = 0.65
    ) -> Dict[str, float]:
        activation: Dict[str, float] = defaultdict(float)
        frontier: List[Tuple[str, float]] = [(e.strip().lower(), 1.0) for e in seed_entities]

        visited: Set[Tuple[str, int]] = set()
        for current_depth in range(depth + 1):
            next_frontier: List[Tuple[str, float]] = []
            for node, energy in frontier:
                if (node, current_depth) in visited:
                    continue
                visited.add((node, current_depth))
                activation[node] = max(activation[node], round(energy, 4))

                if current_depth < depth:
                    for edge in self.adj.get(node, []):
                        if edge.negated:
                            continue
                        propagated = energy * min(1.5, edge.weight) * decay
                        if propagated > 0.05:
                            next_frontier.append((edge.target_id, propagated))
            frontier = next_frontier

        return dict(sorted(activation.items(), key=lambda x: x[1], reverse=True))

    def query_triplets(self, entity: str) -> List[SemanticEdge]:
        key = entity.strip().lower()
        return list(self.adj.get(key, []))
