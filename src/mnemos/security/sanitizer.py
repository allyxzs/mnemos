import re
from typing import List, Pattern


class MemoryPoisoningError(Exception):
    """Disparada quando uma tentativa de injeção ou corrupção cognitiva é detectada."""


class CognitiveSanitizer:
    """Inspetor de segurança contra Prompt Injection persistente e envenenamento de memória."""

    INJECTION_PATTERNS: List[Pattern[str]] = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"system\s*override", re.IGNORECASE),
        re.compile(r"forget\s+everything", re.IGNORECASE),
        re.compile(r"disregard\s+all\s+rules", re.IGNORECASE),
        re.compile(r"<script.*?>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"\[SYSTEM\s*:\s*OVERRIDE\]", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    ]

    @classmethod
    def validate(cls, content: str) -> str:
        if not content or not content.strip():
            raise ValueError("O conteúdo da memória não pode ser vazio.")

        for pattern in cls.INJECTION_PATTERNS:
            if pattern.search(content):
                raise MemoryPoisoningError(
                    f"Tentativa de Memory Poisoning bloqueada pelo padrão: {pattern.pattern}"
                )

        return content.strip()
