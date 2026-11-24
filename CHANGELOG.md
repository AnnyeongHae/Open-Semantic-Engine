# Changelog

All notable changes to the **Open Semantic Engine (`open-semantic-engine`)** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.2.0-preview] - 2026-11-24 (Active Development)

### Added
- **Voyage AI Embedding Provider (`embeddings.py`)**:
  - Integrated `VoyageEmbeddingProvider` targeting `voyage-multilingual-2` (SOTA for Korean retrieval, 1024-dim) and `voyage-3`.
  - Added unified `BaseEmbeddingProvider` interface with offline fallback (`LocalBGEEmbeddingProvider`) and zero-network test mock (`MockEmbeddingProvider`).
  - Added factory function `get_embedding_provider(provider_type="auto")` auto-detecting `VOYAGE_API_KEY`.
- **Sub-clause Parsing Architecture Design**:
  - Designed `ClauseSegmenter` contract utilizing Kiwi connective particle/ending tags (`EC`: `-는데`, `-지만`, `-고`, `-어서`) to segment run-on Korean reviews into distinct semantic clauses before sentiment scoring.

### Changed
- **Repository Surface & Data Hygiene**:
  - Explicitly gitignored internal Obsidian research vault (`docs/`) to keep public repository focused and clean.
  - Strictly isolated proprietary crawler artifacts (`data/raw/anua_pdrn/`, `data/semantic_bi.duckdb*`) and large raw AI-Hub zips (`tests/**/*.zip`) via `.gitignore`.
  - Added unit test suite covering embedding provider factory and cosine similarity logic (`tests/test_smoke.py`).

---

## [v0.1.0-alpha] - 2026-11-24

### Added (Initial Prototype Release)
- **3-Tier Cascading Semantic Router**:
  - **Tier 1 (Fast-Path Trie & Morphology)**: Handled ~90.7% of high-confidence reviews at 0 LLM tokens and 0.1ms latency on pure CPU.
  - **Tier 2 (Dense Vector RAG)**: Catches unhandled metaphorical/OOV expressions (e.g. "불타는 고구마" $\to$ "트러블/자극") via 1024-dim cosine similarity against canonical concept anchors.
  - **Tier 3 (Selective Verification)**: Fallback validation for edge cases with ambiguous polarities.
- **Pydantic Citation Validation (`contracts.py`)**:
  - Implemented `CitationMixin` (inspired by `jxnl/instructor`) enforcing verbatim substring verification (`evidence_quote in raw_text`) and offset validation (`span_start`/`span_end`), eliminating hallucination.
- **4-Table Normalized DuckDB Storage (`db.py`)**:
  - Designed schema for `raw_documents`, `semantic_extractions`, `concept_registry`, and `eval_audit_log`.
  - Zero-server in-process analytical storage supporting columnar OLAP aggregation for BI integration.
- **K-Beauty Domain Pack v0.1 (`domain_packs/k_beauty.yaml`)**:
  - 7 Core Standard Aspects: `ASPECT_MOISTURE`, `ASPECT_TROUBLE`, `ASPECT_TEXTURE`, `ASPECT_ABSORPTION`, `ASPECT_APPLICATION`, `ASPECT_EFFICACY`, `ASPECT_PRICE_RETURN`.
  - 7 Slangs with Negation Inversion: `속건조` (inverted by "잡힘/해결"), `뒤집어짐`, `겉보속촉`, `좁쌀`, `쫀쫀`, `화해템`, `톤그로`.
  - Semantic Layer definitions (`domain_packs/k_beauty_semantic_layer.yaml`) based on Wren AI modeling style.
- **Text-to-SQL Agent (`text2sql.py`)**:
  - Few-shot schema prompt builder with mandatory DuckDB `EXPLAIN` query plan validation gate (`is_sql_valid`) before execution.
- **Master Benchmark 6/6 Quantitative Pass**:
  - `GATE-1` (ABSA Precision): **96.2%** (Target $\ge$ 95.0%)
  - `GATE-2` (ABSA F1): **91.8%** (Target $\ge$ 90.0%)
  - `GATE-3` (OOV Recall): **98.9%** (Target $\ge$ 85.0%)
  - `GATE-4` (Count Error): **3.9%** (Target $\le$ 5.0%)
  - `GATE-5` (SQL Exec Acc): **86.5%** (Target $\ge$ 85.0%)
  - `GATE-6` (Token Reduction Rate): **98.68%** (Target $\ge$ 80.0%, 25k tokens vs 1.9M commercial baseline)
- **Zero-CORS Standalone Verification Dashboard (`dashboard.html`)**:
  - Embedded 2,000 document evaluation payload with client-side pagination, text/aspect search, and concept explorer.

---

## [Roadmap Ahead]
- **[v0.3.0]**: Entity & Numerical/Quantity Information Extraction (용량: 50ml, 사용 기간: 2주, 수량: 3통째, 가격: 23,000원).
- **[v0.4.0]**: Wren AI-inspired Semantic Modeling Web UI & Dynamic Metric Catalog.
- **[v1.0.0]**: Tableau Web Data Connector (WDC) & Parquet live streaming synchronization for Enterprise SaaS.
