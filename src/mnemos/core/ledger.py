import hashlib
import hmac
from typing import Dict, List, Optional, Tuple

from mnemos.core.models import MemoryNode


class MerkleMemoryLedger:
    """
    Auditoria criptográfica encadeada (Merkle-DAG + HMAC-SHA256)
    com suporte a Auto-Cura (Self-Healing) contra corrupção de estado em memória.
    """

    GENESIS_HASH = "GENESIS_00000000000000000000000000000000"

    def __init__(self, secret_key: str = "mnemos-default-sovereign-key") -> None:
        self._secret = secret_key.encode("utf-8")
        self._chain: List[str] = []
        self._snapshots: Dict[str, MemoryNode] = {}
        self.quarantined_ids: List[str] = []

    @property
    def head_hash(self) -> str:
        return self._chain[-1] if self._chain else self.GENESIS_HASH

    def sign_hash(self, content_hash: str) -> str:
        return hmac.new(self._secret, content_hash.encode("utf-8"), hashlib.sha256).hexdigest()

    def append(self, node: MemoryNode) -> str:
        node.parent_hash = self.head_hash
        node_hash = node.content_hash
        node.hmac_signature = self.sign_hash(node_hash)
        self._chain.append(node_hash)
        self._snapshots[node_hash] = node.model_copy(deep=True)
        return node_hash

    def verify_integrity(self, live_nodes: Optional[Dict[str, MemoryNode]] = None) -> bool:
        expected_parent = self.GENESIS_HASH
        for h in self._chain:
            snap = self._snapshots.get(h)
            if not snap:
                return False
            if snap.parent_hash != expected_parent:
                return False
            if snap.content_hash != h:
                return False
            if snap.hmac_signature != self.sign_hash(h):
                return False
            if live_nodes is not None and snap.id in live_nodes:
                live = live_nodes[snap.id]
                if live.content_hash != h or live.hmac_signature != snap.hmac_signature:
                    return False
            expected_parent = h
        return True

    def heal_live_state(self, live_nodes: Dict[str, MemoryNode]) -> Tuple[int, List[str]]:
        healed_count = 0
        healed_ids: List[str] = []

        for h in self._chain:
            snap = self._snapshots.get(h)
            if not snap or snap.id not in live_nodes:
                continue
            live = live_nodes[snap.id]
            if live.content_hash != h or live.hmac_signature != snap.hmac_signature:
                live.content = snap.content
                live.created_at = snap.created_at
                live.parent_hash = snap.parent_hash
                live.hmac_signature = snap.hmac_signature
                healed_count += 1
                healed_ids.append(live.id)
                if live.id not in self.quarantined_ids:
                    self.quarantined_ids.append(live.id)

        return healed_count, healed_ids

    def compute_state_root(self) -> str:
        if not self._chain:
            return hashlib.sha256(b"EMPTY_MNEMOS_STATE").hexdigest()
        combined = "".join(self._chain).encode("utf-8")
        return hashlib.sha256(combined).hexdigest()
