# Mnemos v2.0 — Hyper-Cognitive Memory & Cryptographic State Engine

**Mnemos v2.0** é um motor de memória cognitiva tri-camada com auditoria criptográfica em cadeia (Merkle-DAG) e persistência SQLite WAL para agentes autônomos de alta governança.

## Arquitetura Core (v2.0)

1. **Tri-Tier Memory Hierarchy**:
   - **L1 (`WORKING`)**: Buffer volátil de alta velocidade com evicção automática baseada em pressão cognitiva.
   - **L2 (`EPISODIC`)**: Armazenamento vetorial acoplado à **Curva de Esquecimento de Ebbinghaus** ($R = e^{-\lambda \Delta t / S}$).
   - **L3 (`SEMANTIC`)**: Grafo dirigido de conhecimento com **Spreading Activation** (Propagação de Ativação Neural) e resolução dialética de contradições.
2. **Merkle-DAG Provenance Ledger**:
   - Cada memória inserida ou consolidada recebe um `SHA-256` encadeado ao `parent_hash` anterior e uma assinatura `HMAC-SHA256` opcional.
3. **Cognitive Sanitizer (Anti-Memory Poisoning)**:
   - Inspeção léxica, heurística e de entropia contra *Prompt Injection* persistente e *Context Hijacking*.
4. **Dialectical Reconsolidation Daemon**:
   - Poda memórias episódicas decaídas, funde redundâncias semânticas (Long-Term Potentiation) e detecta conflitos factuais no grafo semântico.
5. **Persistência Transacional SQLite (WAL)**:
   - Snapshot e restauração atômica de nós, arestas semânticas e cadeia Merkle.

## Instalação Rápida (Kali Linux / Debian / Ubuntu)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Uso via CLI

```bash
# Executar demonstração completa e auditoria Merkle
python3 -m mnemos.cli demo

# Rodar suíte de testes
pytest -v
```
