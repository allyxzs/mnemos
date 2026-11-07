import math
import re
from collections import Counter
from typing import List, Pattern


class MemoryPoisoningError(Exception):
    """Disparada quando uma tentativa de injeção ou corrupção cognitiva é detectada."""


class CognitiveSanitizer:
    """
    Inspetor de segurança contra Prompt Injection persistente, Context Hijacking
    e payloads ofuscados de alta entropia.
    """

    INJECTION_PATTERNS: List[Pattern[str]] = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"system\s*override", re.IGNORECASE),
        re.compile(r"forget\s+everything", re.IGNORECASE),
        re.compile(r"disregard\s+all\s+rules", re.IGNORECASE),
        re.compile(r"<script.*?>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"\[SYSTEM\s*:\s*OVERRIDE\]", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
        re.compile(r"dump\s+(all\s+)?(secret|private)\s+keys", re.IGNORECASE),
    ]

    @staticmethod
    def shannon_entropy(text: str) -> float:
        if not text:
            return 0.0
        counts = Counter(text)
        length = len(text)
        return -sum((c / length) * math.log2(c / length) for c in counts.values())

    @classmethod
    def validate(cls, content: str, max_entropy: float = 6.2) -> str:
        if not content or not content.strip():
            raise ValueError("O conteúdo da memória não pode ser vazio.")

        for pattern in cls.INJECTION_PATTERNS:
            if pattern.search(content):
                raise MemoryPoisoningError(
                    f"Tentativa de Memory Poisoning bloqueada pelo padrão: {pattern.pattern}"
                )

        if len(content) > 64 and cls.shannon_entropy(content) > max_entropy:
            raise MemoryPoisoningError(
                "Payload bloqueado por anomalia de entropia de Shannon (possível ofuscação)."
            )

        return content.strip()
