# Mnemos v2.5 — Sovereign Hyper-Cognitive Memory & Cryptographic State Engine

![CI Status](https://github.com/allyxzs/mnemos/actions/workflows/ci.yml/badge.svg)
![Version](https://img.shields.io/badge/version-2.5.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**Mnemos v2.5** é um motor de memória cognitiva tri-camada com auditoria criptográfica em cadeia (Merkle-DAG + HMAC-SHA256), **Auto-Cura de Estado (Self-Healing)**, busca híbrida **Quad-Fusion (Vetorial + BM25 Lexical + Retenção Ebbinghaus + Spreading Activation)** e persistência transacional SQLite WAL.

## Novidades da Versão 2.5 (Upgrade & CI Fix)

1. **Quad-Fusion Hybrid Recall**:
   - Combina **Similaridade Vetorial (Cosseno)** + **Okapi BM25 Lexical** + **Curva de Esquecimento de Ebbinghaus** ($R = e^{-\lambda \Delta t / S}$) + **Propagação de Ativação Neural no Grafo (L3)**.
2. **Self-Healing Cryptographic Ledger**:
   - Além de detectar adulterações na cadeia Merkle-DAG/HMAC, o motor agora isola nós corrompidos em quarentena forense e reconstrói a integridade da cadeia automaticamente a partir do snapshot íntegro.
3. **Shannon Entropy & Heuristic Sanitizer**:
   - Bloqueia *Prompt Injection* persistente, payloads ofuscados de alta entropia e tentativas de *Context Hijacking*.
4. **Full SQLite WAL Hydration & Snapshot**:
   - Restauração completa (`_hydrate_from_store`) de nós L1/L2/L3, arestas semânticas e cadeia criptográfica ao iniciar o agente.
5. **CLI Expandida**:
   - Comandos `mnemos demo`, `mnemos audit` e `mnemos benchmark`.

## Instalação Rápida

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Uso via CLI

```bash
# Demonstração completa (Ingestão, Grafo Dialético, Anti-Poisoning e Self-Healing)
mnemos demo

# Auditoria criptográfica rápida (usada no GitHub Actions CI)
mnemos audit

# Benchmark de performance e latência cognitiva
mnemos benchmark

# Rodar linter e suíte de testes
ruff check src/ tests/
pytest -v
```
