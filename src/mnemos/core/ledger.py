import hashlib
import hmac
from typing import Dict, List, Optional
from mnemos.core.models import MemoryNode


class MerkleMemoryLedger:
    """Auditoria criptográfica encadeada (Merkle-DAG + HMAC) contra adulteração de estado."""

    GENESIS_HASH = "GENESIS_00000000000000000000000000000000"

    def __init__(self, secret_key: str = "mnemos-default-sovereign-key") -> None:
        self._secret = secret_key.encode("utf-8")
        self._chain: List[str] = []
        self._nodes_by_hash: Dict[str, MemoryNode] = {}

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
        self._nodes_by_hash[node_hash] = node.model_copy(deep=True)
        return node_hash

    def verify_integrity(self) -> bool:
        expected_parent = self.GENESIS_HASH
        for h in self._chain:
            node = self._nodes_by_hash.get(h)
            if not node:
                return False
            if node.parent_hash != expected_parent:
                return False
            if node.content_hash != h:
                return False
            if node.hmac_signature != self.sign_hash(h):
                return False
            expected_parent = h
        return True

    def compute_state_root(self) -> str:
        if not self._chain:
            return hashlib.sha256(b"EMPTY_MNEMOS_STATE").hexdigest()
        combined = "".join(self._chain).encode("utf-8")
        return hashlib.sha256(combined).hexdigest()
