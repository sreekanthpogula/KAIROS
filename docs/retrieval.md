# Retrieval Architecture

## The hybrid pipeline, end to end

```
query -> query understanding -> metadata/ontology filters -> ACL filter ->
vector retrieval -> lexical retrieval -> fusion/rerank -> final context -> (RAG) answer
```

`RetrievalService.search()` (`app/retrieval/service.py`) runs every stage in that order for every call — `search` and `rag` both go through it, RAG just adds an answer-synthesis step on top:

1. **Query understanding** (`QueryUnderstandingService.understand()`) reuses `RuleBasedClassifier` — the exact same classifier that decides what a *document* is — against the raw query text. If it matches with at least `MIN_DOMAIN_CONFIDENCE = 0.15` confidence, the query gets a soft `domain`/`document_type`/`ontology_id` hint plus extracted `topics`/`entities`. That threshold is deliberately low: queries are short, so raw keyword-hit scores are structurally much smaller than a full document's, and a single decisive keyword ("termination") should be enough to set a hint. This is safe to set low because the hint never hard-filters results — it only feeds the reranker's ontology/metadata scores (below) as one signal among several.
2. **Explicit filters** — optional `domain_filter`/`document_type_filter` request parameters narrow the SQL query directly.
3. **ACL filter** — every remaining candidate chunk is checked against `requester_group`: `chunk.allowed_groups` empty means open to everyone, otherwise the requester's group must be in the list (`RetrievalService._is_allowed`). This runs *before* any scoring, so an excluded chunk never gets a chance to be ranked, let alone returned.
4. **Vector retrieval** (`NumpyVectorIndexBackend.semantic_search`) — cosine similarity between the query embedding and every allowed candidate's stored embedding, computed in-process with numpy.
5. **Lexical retrieval** (`LexicalIndexService.search`) — BM25 (`rank_bm25`) rebuilt fresh over the allowed candidate set for this query, stopword-filtered.
6. **Fusion/rerank** (`Reranker.score`) — combines semantic, lexical, ontology, and metadata scores into one explainable final score per chunk.

## The explainable score breakdown

Every scored chunk carries its full breakdown, not just a final rank — this is deliberate: a manager (or an engineer debugging a bad result) can see *why* a chunk ranked where it did.

```python
final_score = (
    weight_semantic  * semantic_score   # 0.45 — cosine similarity, vector index
  + weight_lexical   * lexical_score    # 0.25 — BM25, saturating transform
  + weight_ontology  * ontology_score   # 0.20 — does chunk domain/type match query understanding?
  + weight_metadata  * metadata_score   # 0.10 — classification confidence + topic/entity overlap
)
```

All four weights are `Settings` fields (`WEIGHT_SEMANTIC`/`WEIGHT_LEXICAL`/`WEIGHT_ONTOLOGY`/`WEIGHT_METADATA`), tunable without a code change. `ontology_score` defaults to a neutral `0.5` (not `0`) when the query understanding found no domain/type hint at all, specifically so queries without a clear ontology signal aren't unfairly penalized just for being hard to categorize. `metadata_score` blends the chunk's own classification confidence (70%) with topic/entity overlap between the query and the chunk (30%) — a chunk from a confidently-classified document, on-topic with the query, scores higher than an equally-matched chunk from a document the system itself wasn't sure about.

`Reranker` is explicitly documented as a POC stand-in: *"A weighted-sum heuristic, explicitly labeled as a POC stand-in — the interface is designed so a real cross-encoder/reranker model could replace `Reranker.score()` without changing anything upstream (retrieval still produces the same semantic/lexical candidate scores either way)."* A cross-encoder reranker (jointly scoring query+chunk text rather than combining independently-computed signals) is the natural production upgrade — see [decisions.md](decisions.md) ADR-004 and [production-scaling.md](production-scaling.md).

## The bug: ACL narrowing inflated a false 1.0 confidence

This is worth documenting in detail because it's a real bug, found and fixed during the build, not a hypothetical.

**What went wrong.** BM25 lexical scores were originally normalized with min-max scaling *within whatever candidate pool made it past the ACL filter for that specific query*. That's fine when the candidate pool is the whole corpus — the best match in a large, topically diverse pool is usually a genuinely strong match. But once ACL filtering narrows the pool down to, say, fifteen documents that are all *irrelevant* to the query (because every genuinely relevant document was excluded by the requester's access level), min-max normalization still rescales whatever the best-of-that-bad-lot score was up to `1.0` — turning a coincidental, weak, single-keyword overlap into a lexical score indistinguishable from a perfect match. The reranker would then confidently surface that weak match, and worse, RAG would synthesize an answer from it as if it were relevant.

**The fix.** Two changes, both in `app/retrieval/lexical_index.py`:

1. **Stopword filtering** on tokenization (`_STOPWORDS` set), so a coincidental overlap on words like "the," "any," or "does" doesn't count as a meaningful match at all.
2. **An absolute saturating transform on the raw BM25 score, instead of relative min-max normalization against the candidate pool:**

```python
BM25_SATURATION_K = 6.0
score = 1.0 - math.exp(-max(0.0, raw_bm25_score) / BM25_SATURATION_K)
```

The code comment is explicit about why this specific fix matters: *"This matters once ACL filtering narrows the pool to e.g. 15 unrelated documents: min-max normalization would inflate the best-of-a-bad-lot match to a false 1.0, while this absolute scale correctly reports it as still weak."* `K=6.0` is calibrated so a genuine multi-keyword match (raw score ~6–8) lands around 0.6–0.75, while a coincidental single-stopword-adjacent overlap (raw ~0–1) stays near zero — regardless of what else is or isn't in the candidate pool that query happened to narrow down to.

**The second layer of defense.** Even with the lexical fix, `RAGService` adds an independent floor on the *final* blended score before it will treat anything as a real answer:

```python
MIN_RELEVANT_SCORE = 0.30

relevant = [s for s in retrieval.scored if s.final_score >= MIN_RELEVANT_SCORE]
if not relevant:
    return "No documents you have access to contain information relevant to this question."
```

This is what makes the ACL demo scenario work correctly: an "engineering" group user asking *"What are the provider termination requirements?"* gets every genuinely relevant legal/financial chunk excluded by the ACL filter before scoring even happens. Whatever technical-domain chunks are left over score below `0.30` once the lexical fix is in place, so the answer comes back honest — *"no accessible documents are relevant"* — instead of a confidently synthesized answer built from irrelevant leftover technical content. Groundedness reporting (`RAGService._groundedness`) is calibrated to the same score scale: `>= 0.45` is "high," `>= 0.30` (the floor) is "medium," and anything below the floor never reaches an answer at all. On the two canonical demo queries, groundedness comes back "high" for the provider-termination question and "medium" for the reimbursement-policy question — both correctly answered, with a real (if honestly modest) score margin, not a saturated 1.0.

## Why vector search is numpy, not pgvector, in this POC

`VectorIndexBackend` is an interface with one POC implementation, `NumpyVectorIndexBackend` — load the candidate set's stored embeddings (already narrowed by ACL and filters) and rank by cosine similarity in-process. This is correct and fast enough at the POC's scale (dozens to hundreds of chunks) and is explicit about its own limits: *"do not pretend to process 1TB locally."* `VECTOR_BACKEND=pgvector` is a real, documented configuration value in `Settings`, and the embedding storage model (`Embedding.vector` as a portable JSON float array) is designed to support a native `vector` column alongside it — but it requires an actual PostgreSQL+pgvector instance to exercise, which this local dev environment doesn't provision by default, so it is **not** exercised end-to-end here. Swapping it in is intended to require zero changes to `RetrievalService` or anything above it. Similarly, lexical search rebuilds a fresh BM25 index over the candidate set on every single query — fine at this scale, but explicitly noted as a POC simplification; a production system would maintain a persistent inverted index (Postgres `tsvector`/GIN, or a dedicated search engine) instead of rebuilding per request.

## RAG answers: extractive and deterministic in DEMO_MODE

`RAGService._deterministic_answer()` picks, from each of the top retrieved chunks, whichever sentences have the highest word-overlap with the query's own (stopword-filtered) tokens, deduplicates, and joins them — no generative model involved. The same query always produces the same answer, and every word in it is traceable to a specific sentence in a specific retrieved chunk. `LLM_MODE` (when actually configured) swaps in a real generative call over the same retrieved context, instructed to cite sources inline by index — but the retrieval, ACL, and relevance-floor logic upstream of it is identical either way. Every answer, in either mode, carries structured `Citation`s (`document_id`, `filename`, `section`, `page_start`/`page_end`, `chunk_id`, `final_score`) so an answer's provenance is always inspectable — see [security.md](security.md) for the ACL story and `GET /api/documents/{id}/lineage` for how a citation traces further back to its source document.
