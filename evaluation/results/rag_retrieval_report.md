# RAG Retrieval Benchmark Report

* **Generated**: 2026-10-09 21:06:42
* **Mode**: Local ONNX all-MiniLM-L6-v2
* **Indexing Time**: 1.50s
* **Queries Evaluated**: 15

## 1. Summary Performance Metrics

| Retrieval Mode | Recall@1 | Recall@3 | Recall@5 | MRR (Mean Reciprocal Rank) |
|---|:---:|:---:|:---:|:---:|
| **Dense** | 93.33% | 100.00% | 100.00% | 0.9667 |
| **Bm25** | 66.67% | 80.00% | 86.67% | 0.7278 |
| **Hybrid** | 73.33% | 93.33% | 100.00% | 0.8356 |

## 2. Per-Query Breakdown Table

| Query | Target Symbol | Dense Rank | BM25 Rank | Hybrid Rank |
|---|---|:---:|:---:|:---:|
| `factorial negative input` | `factorial` | 1 | 1 | 1 |
| `prime number check` | `is_prime` | 1 | 3 | 2 |
| `fibonacci sequence negative` | `fibonacci` | 1 | 1 | 1 |
| `clamp between min and max` | `clamp` | 1 | 1 | 1 |
| `raise base to exponent` | `power` | 1 | 1 | 1 |
| `truncate text suffix max length` | `truncate` | 1 | 1 | 1 |
| `make lowercase url slug` | `slugify` | 1 | - | 2 |
| `count word occurrences punctuation` | `count_words` | 1 | 4 | 1 |
| `capitalize every word preserve spaces` | `capitalize_words` | 1 | 1 | 1 |
| `split list into chunks` | `chunk_list` | 1 | - | 5 |
| `flatten nested list recursively` | `flatten` | 1 | 1 | 1 |
| `remove duplicate items preserve order` | `deduplicate` | 1 | 1 | 1 |
| `first item matching predicate default` | `find_first` | 1 | 1 | 1 |
| `euclidean distance between points` | `distance` | 1 | 1 | 1 |
| `email validation username domain` | `validate_email` | 2 | 3 | 3 |

## 3. LaTeX Dissertation Table

```latex
\begin{table}[h]
\centering
\begin{tabular}{lcccc}
\hline
\textbf{Retrieval Strategy} & \textbf{Recall@1} & \textbf{Recall@3} & \textbf{Recall@5} & \textbf{MRR} \\
\hline
Dense & 93.33\% & 100.00\% & 100.00\% & 0.9667 \\
Bm25 & 66.67\% & 80.00\% & 86.67\% & 0.7278 \\
Hybrid & 73.33\% & 93.33\% & 100.00\% & 0.8356 \\
\hline
\end{tabular}
\caption{Code Retrieval Performance across Dense, BM25, and Hybrid Fused Strategies.}
\label{tab:rag_retrieval_results}
\end{table}
```
