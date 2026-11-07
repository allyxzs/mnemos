from __future__ import annotations

import hashlib
import json
import math
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryTier(str, Enum):
    WORKING = "L1_WORKING"
    EPISODIC = "L2_EPISODIC"
    SEMANTIC = "L3_SEMANTIC"


class MemoryNode(BaseModel):
    id: str
    content: str
    tier: MemoryTier = MemoryTier.WORKING
    embedding: List[float] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    access_count: int = Field(default=1, ge=1)
    created_at: float = Field(default_factory=time.time)
    last_accessed: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    parent_hash: Optional[str] = None
    hmac_signature: Optional[str] = None

    @property
    def content_hash(self) -> str:
        payload = json.dumps(
            {
                "id": self.id,
                "content": self.content,
                "created_at": round(self.created_at, 4),
                "parent_hash": self.parent_hash,
            },
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def retention_score(
        self, current_time: Optional[float] = None, decay_rate: float = 0.0001
    ) -> float:
        now = current_time or time.time()
        delta_t = max(0.0, now - self.last_accessed)
        stability = max(0.1, self.importance * math.log2(self.access_count + 1.5))
        return math.exp(-(decay_rate * delta_t) / stability)


class SemanticEdge(BaseModel):
    source_id: str
    target_id: str
    relation: str
    weight: float = Field(default=1.0, ge=0.0)
    negated: bool = False
    evidence_hashes: List[str] = Field(default_factory=list)
    updated_at: float = Field(default_factory=time.time)


class ConflictRecord(BaseModel):
    subject: str
    relation: str
    existing_target: str
    conflicting_target: str
    resolution: str
    detected_at: float = Field(default_factory=time.time)
