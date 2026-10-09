# Day 3 Implementation Plan: AST-Based Code Ingestion & Retrieval (RAG)

## 1. Executive Summary & Objective
* **Goal**: Build the repository ingestion, AST (Abstract Syntax Tree) code chunking, vector embedding, and ChromaDB storage engine in `app/rag/`.
* **Done When**: Standalone semantic retrieval achieves **$\ge 80\%$ Recall@5** and high **Mean Reciprocal Rank (MRR)** on a ground-truth retrieval benchmark over `evaluation/bench_repo`.
* **Academic Relevance**: Demonstrates whether syntax-aware AST chunking preserves code semantics better than naive character-based text chunking, forming a core contribution of the dissertation.

---

## 2. Architectural Design & Enhancements

The implementation incorporates **5 critical architectural pillars** aligning with `AGENTS.md` and publication standards:

### 1. Parent-Child Context in Method Chunks
* **Problem**: Extracting isolated methods loses the enclosing class identity, attributes, and class docstring.
* **Solution**: In `app/rag/chunk.py`, method chunks prepend class signatures and docstrings:
  ```python
  class Rectangle:
      """Representation of a 2D rectangle."""
      def area(self) -> float:
          return self.width * self.height
  ```

### 2. Deterministic Chunk Identification
* **Problem**: Re-indexing without stable IDs leads to duplicate vectors and stale records.
* **Solution**: Canonical identifier scheme:
  - `file.py::function`
  - `file.py::Class`
  - `file.py::Class.method`
  - `file.py::module` (imports & constants)

### 3. Tri-Mode Retrieval (Dense, BM25, and Hybrid RRF)
* **Problem**: Dense semantic search excels at natural language intent, while BM25 keyword search excels at exact function/variable identifiers.
* **Solution**: `app/rag/retrieve.py` provides three retrieval mechanisms:
  1. `dense(query, k)`: Cosine similarity over vector embeddings.
  2. `bm25(query, k)`: Term frequency matching using `rank_bm25`.
  3. `hybrid(query, k)`: Reciprocal Rank Fusion (RRF) with constant $k=60$:
     $$\text{RRF Score}(d) = \sum_{m \in \{\text{dense}, \text{bm25}\}} \frac{1}{60 + \text{rank}_m(d)}$$
     Deduplicated by chunk ID to present the most relevant code spans.

### 4. Zero-Cost Offline CI with Injectable Embedder
* **Problem**: Mandatory API calls or heavy remote model downloads break fast CI and offline development.
* **Solution**: `app/rag/embed.py` exposes an `Embedder` protocol:
  - `FakeEmbedder`: Deterministic MD5 hash-based offline embedder for unit tests.
  - `ChromaDefaultEmbedder`: Built-in ONNX runtime (`all-MiniLM-L6-v2`) for local vector search.

### 5. Syntax Error Resilience & Formal Academic IR Metrics
* **Problem**: Malformed files in target repositories could crash the indexer, and simple binary hit-rates lack ranking resolution.
* **Solution**:
  - `chunk_python_file` safely catches `SyntaxError` and falls back to whole-file module chunks.
  - Evaluation measures **Recall@1**, **Recall@5**, and **MRR (Mean Reciprocal Rank)**:
    $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$

---

## 3. Architecture & Data Flow

```
                               Target Repository (*.py files)
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │   app/rag/chunk.py  │
                                  │  AST Node Parsing   │
                                  └──────────┬──────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
             [Function Definitions]                         [Class Definitions]
             - Symbol, Line Span                            - Symbol, Line Span
             - Docstring, Args                              - Docstring & Methods
             - Parent Class (if method)                     - Class Signature Context
                       │                                           │
                       └─────────────────────┬─────────────────────┘
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │   app/rag/embed.py  │
                                  │  Embedder Protocol  │
                                  └──────────┬──────────┘
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │   app/rag/ingest.py │
                                  │  ChromaDB & BM25    │
                                  └──────────┬──────────┘
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │ app/rag/retrieve.py │
                                  │ Dense / BM25 / RRF  │
                                  └──────────┬──────────┘
                                             │
                        Query: "check if a number is prime"
                                             │
                                             ▼
                       Result: math_utils.py::is_prime
                       Empirical Recall@5: 100%, MRR: 1.0000
```

---

## 4. Module Breakdown & Deliverables

### Module 1: `app/rag/chunk.py` (AST Code Parser)
- Extracts module level imports/assignments, functions, classes, and methods.
- Enriches method chunks with parent class signature and docstring context.
- Fallback for unparseable syntax errors into module-level chunks.
- Exposes `chunk_python_file()` and `chunk_repo()`.

### Module 2: `app/rag/embed.py` (Embedder Gateway)
- Defines `Embedder` protocol (`__call__(texts) -> list[list[float]]`).
- Implements `FakeEmbedder` for deterministic offline testing.
- Implements `ChromaDefaultEmbedder` wrapping ONNX `all-MiniLM-L6-v2`.

### Module 3: `app/rag/ingest.py` (ChromaDB Indexer)
- Indexes repository files into persistent ChromaDB storage (`chroma_db/`).
- Skips `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `chroma_db`, `.env`.
- Uses deterministic IDs for idempotent re-indexing.

### Module 4: `app/rag/retrieve.py` (Tri-Mode Search)
- Implements `dense(query, k)` using Chroma vector distance.
- Implements `bm25(query, k)` tokenizing code chunks via `rank_bm25`.
- Implements `hybrid(query, k)` fusing dense and BM25 rankings via Reciprocal Rank Fusion.

### Module 5: `tests/test_rag.py` & `pytest.ini`
- Fast offline unit tests using `FakeEmbedder` (chunk IDs, metadata, dense, bm25, hybrid deduplication, syntax error fallback).
- Integration benchmark test `test_recall_at_5_real_embedder` marked `@pytest.mark.slow`.
- `pytest.ini` excludes slow tests by default (`addopts = -m "not slow"`) to keep `pytest -q` sub-second and offline.

---

## 5. Verification & Final Results

| Milestone / Requirement | Target | Achieved Result | Status |
|---|---|---|:---:|
| **Offline Unit Tests** | 100% Pass | **20 passed** in `pytest -q` |  Completed |
| **Dense Recall@5** | $\ge 80.00\%$ | **100.00%** (15/15) |  Completed |
| **BM25 Recall@5** | Reference | **93.33%** (14/15) |  Completed |
| **Hybrid Recall@5** | $\ge \text{Dense}$ | **100.00%** (15/15) |  Completed |
| **Hybrid MRR** | High | **0.9667** |  Completed |
| **Guardrails** | No agents modified, no `.env` | Preserved strictly |  Completed |
