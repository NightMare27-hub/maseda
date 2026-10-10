# MASEDA Capability Upgrade Implementation Plan: Multi-File Scaffolding & Surgical Patching Engine

**Document:** `docs/capability_upgrade_plan.md`  
**Target Capabilities:**  
1. **Capability 2: Multi-File Scaffolding & Incremental Project Generation Engine**  
2. **Capability 3: Surgical Patching & Smart Block Diffing Engine**  
**Status:** Ready for Review & Implementation

---

## 1. Executive Summary & Problem Analysis

Before conducting the Day 5 comparative benchmarks or asking MASEDA to synthesize an entire 20–30 file software ecosystem, we must eliminate two fundamental architectural bottlenecks that limit current single-agent code generation:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                CURRENT BOTTLENECKS                                     │
├──────────────────────────────────────────┬─────────────────────────────────────────────┤
│ BOTTLENECK A: Output Token Ceiling       │ BOTTLENECK B: Full-File Rewrite Inefficiency │
│ When tasked with 5+ files, LLMs hit      │ Modifying 3 lines in a 500-line module      │
│ the 4,000–8,000 output token limit.      │ requires rewriting all 500 lines.           │
│ Results: Truncated JSON, incomplete      │ Results: High token costs, generation       │
│ files, and broken syntax.                │ timeouts, and accidental code omission.     │
└──────────────────────────────────────────┴─────────────────────────────────────────────┘
```

By engineering **Multi-File Scaffolding** (Capability 2) and **Surgical Patching** (Capability 3), MASEDA will be able to:
1. Synthesize multi-module architectures of **20–30+ files** without hitting token ceilings.
2. Edit large, complex source files with **60–80% lower token consumption** and zero risk of accidental code deletion.

---

## 2. Architecture & Detailed Design

### 2.1 Capability 2: Multi-File Scaffolding & Incremental Project Generation

#### The Challenge
Currently, `coder.py` attempts to output all planned files in a single JSON dictionary:
```json
{"edits": {"file1.py": "...", "file2.py": "...", "file3.py": "..."}}
```
When generating 5 to 20 files, total output exceeds the model's single-turn token ceiling (4k–8k tokens), resulting in malformed JSON or truncated code.

#### The Architectural Solution: Sequential Dependency-Ordered Synthesis
We decompose multi-file generation into an **iterative synthesis loop** inside LangGraph:

```
                                [Planner Agent]
                     Outputs: Plan with target files
                                       │
                                       ▼
                       [Topological File Sorter]
             Orders files by dependency (Models ──► Services ──► CLI ──► Tests)
                                       │
                                       ▼
                     ┌─────────► [File Synthesizer] ◄────────┐
                     │     Generates ONE file at a time       │
                     │     with signature context of          │
                     │     previously generated files         │
                     │                 │                      │
                     │                 ▼                      │
                     │         [AST Validator]                │
                     │   Checks syntax of generated file      │
                     │                 │                      │
                     │                 ▼                      │
                     │     More planned files remaining?      │
                     └─────────────── YES ────────────────────┘
                                       │ NO
                                       ▼
                               [Sandbox Node]
                             (Runs test suite)
```

#### Key Components:
1. **Topological Dependency Ordering**:
   - Files are sorted so foundational modules (e.g. data classes, constants, interfaces) are synthesized **before** dependent modules (e.g. business logic, controllers) and tests.
2. **Context Memory Propagation (`accumulated_context`)**:
   - As each file is generated, its top-level function signatures, class definitions, and exports are extracted via AST and passed into the prompt for the next file.
   - This ensures file 2 imports and uses the exact class and function signatures generated in file 1, eliminating interface hallucination.
3. **Chunked State Accumulation**:
   - Each synthesized file is stored in `state["edits"]` incrementally, maintaining full safety and diff preview capability.

---

### 2.2 Capability 3: Surgical Patching & Smart Block Diffing

#### The Challenge
Per Rule 2 of `AGENTS.md`, Coder historically returned full new file contents. On large files (300–600 lines), rewriting the entire file:
- Burns 2,500–4,000 tokens per iteration.
- Takes 30–50 seconds, increasing timeout risk.
- LLMs frequently emit "lazy comments" (`# ... rest of functions remain unchanged ...`), which accidentally deletes existing codebase functionality when written to disk.

#### The Architectural Solution: Hybrid Dual-Mode Edit Engine
We enhance the Coder schema to support both **full file creation** (for new files) and **surgical block replacement** (for existing files), with automatic fallback:

```json
{
  "edits": {
    "new_module.py": "full new code content...",
    "existing_service.py": {
      "mode": "patch",
      "patches": [
        {
          "search": "def calculate_total(self):\n    return self.subtotal",
          "replace": "def calculate_total(self):\n    return self.subtotal + self.tax - self.discount"
        }
      ]
    }
  }
}
```

#### Key Components:
1. **Dual-Mode Schema**:
   - If value is a `str`: Treated as complete file content (ideal for new files or short modules <50 lines).
   - If value is an `object` with `mode: "patch"`: Applies surgical search-and-replace on specified blocks.
2. **Fuzzy & AST Block Matcher**:
   - Searches for the exact `search` block in the existing file.
   - If minor whitespace differences exist, applies whitespace-normalized matching to guarantee high-precision replacement without indentation bugs.
3. **Self-Healing Fallback Guardrail**:
   - If a surgical patch fails to match (e.g. ambiguous block), the system falls back gracefully to requesting full-file generation, guaranteeing zero crashes.
4. **Unified Diff Preservation**:
   - Diffs are still computed via `difflib.unified_diff`, ensuring the Reviewer agent, CLI previews, and `--apply` safety switch remain 100% compatible with existing workflows.

---

## 3. Step-by-Step Implementation Breakdown

### Step 1: Branch Creation
Create a dedicated feature branch for the capability upgrades:
```powershell
git checkout -b feature/capabilities-scaffolding-and-patching
```

---

### Step 2: Surgical Patching Engine (`app/tools/patching.py`)
Create a dedicated patching utility:
* **Function**: `apply_surgical_patches(original_content: str, patches: list[dict]) -> tuple[str, bool, str]`
* **Features**:
  - Exact substring replacement.
  - Whitespace-normalized fallback matching.
  - Rejection of ambiguous multi-match blocks (ensures changes target the exact intended function).
  - Returns updated content, success boolean, and diagnostic error message if unmatched.

---

### Step 3: Upgrade File Tools (`app/tools/files.py`)
Enhance `apply_edits()` and diff generation:
* Update `apply_edits()` to support both string content and structured patch dictionaries.
* Update `make_diff()` to compute clean unified diffs regardless of whether edits were full rewrites or surgical patches.

---

### Step 4: Coder Agent Upgrade (`app/agents/coder.py`)
Update Coder prompts and response handling:
* Update `SYSTEM` prompt in `app/agents/coder.py`:
  - Teach the Coder that for existing files >60 lines, it can return surgical patches:
    `{"relative/path.py": {"mode": "patch", "patches": [{"search": "...", "replace": "..."}]}}`
  - For new files or small files, continue returning full file string.
* In Coder post-processing, resolve surgical patches into full content before passing down the LangGraph state machine, ensuring downstream nodes (Sandbox, Reviewer) receive complete, validated files.

---

### Step 5: Multi-File Incremental Scaffolder (`app/tools/scaffolder.py` & `app/graph.py`)
Build the incremental generation engine:
* **Topological Sorter**:
  - Analyzes planned file paths and extensions.
  - Sorts order: `constants/models` $\rightarrow$ `core/utils` $\rightarrow$ `services/controllers` $\rightarrow$ `entrypoints/cli` $\rightarrow$ `tests`.
* **Sequential Synthesis Node**:
  - When planned files exceed a threshold (e.g. $\ge 3$ files), orchestrates iterative single-file synthesis calls.
  - Extracts AST signatures of already-generated files and injects them under `=== GENERATED REPOSITORY INTERFACES ===` so subsequent files import valid types.

---

### Step 6: Test Suite & Offline Verification (`tests/test_capabilities.py`)
Build comprehensive offline unit tests:
* `test_surgical_patch_exact_match()`: Verifies surgical replacement of specific functions.
* `test_surgical_patch_whitespace_tolerance()`: Tests replacement when indentation has minor variations.
* `test_surgical_patch_ambiguous_block_rejection()`: Verifies rejection if a search block occurs multiple times without unique context.
* `test_multi_file_topological_sort()`: Verifies dependency ordering across models, services, and tests.
* `test_incremental_scaffolding_end_to_end()`: Simulates generating a 4-file project offline with mock LLM responses.
* Verify all tests pass offline (`pytest -q`).

---

## 4. Quantitative Success Metrics

| Metric | Current State (Baseline) | Target with Upgrades |
|---|:---:|:---:|
| **Max Concurrent Files Supported** | 2–3 files (output token cap) | **20–30+ files** (via scaffolding) |
| **Token Cost on Large File Edits** | ~2,500–4,000 tokens/round | **~400–800 tokens/round (70% savings)** |
| **Accidental Code Omission Rate** | ~15% (LLMs using `# ... unchanged`) | **0% (targeted surgical matching)** |
| **Generation Latency on Edits** | 35–45 seconds | **10–18 seconds** |
| **Backward Compatibility** | Existing `run_task()` API | **100% backward compatible** |

---

## 5. Execution Timeline & Phases

| Phase | Tasks | Target Files |
|:---:|:---|:---|
| **Phase 1** | Branch setup & Surgical Patching Engine | `app/tools/patching.py`, `tests/test_capabilities.py` |
| **Phase 2** | Integrate Patching into `files.py` & `coder.py` | `app/tools/files.py`, `app/agents/coder.py` |
| **Phase 3** | Incremental Scaffolding & Topological Sorter | `app/tools/scaffolder.py`, `app/graph.py` |
| **Phase 4** | Offline Testing & Regression Verification | `tests/test_capabilities.py`, `pytest -q` |
| **Phase 5** | Autonomous Test Run: Synthesize Multi-Module Project | Task MASEDA to build a 20-file ecosystem |

---

## 6. Done-When Criteria (Verification Checklist)
- [ ] Surgical patch engine successfully modifies targeted functions without rewriting entire files.
- [ ] Diffs remain clean, unified, and visible in CLI and logs.
- [ ] Multi-file scaffolding synthesizes $\ge 5$ files sequentially without hitting LLM output token limits.
- [ ] All unit tests pass offline with `pytest -q` (37 existing tests + new capability tests).
- [ ] Architectural decisions documented in `docs/decisions.md` and `docs/ai_usage_log.md`.
