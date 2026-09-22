# Architecture Decision Records

Each ADR below documents a real choice made in this codebase: the problem it responds to, the decision, the alternatives that were considered and rejected, and the honest trade-offs of the choice actually made. These are **POC-scoped defaults, not universal claims** — every ADR says explicitly what would make a different choice more appropriate, and most point at what a production system would likely do instead.

---

## ADR-001: Controlled ontology (taxonomy) vs. knowledge graph

**Problem.** Documents need a shared vocabulary for "what this is" that classification, chunking, security, and search can all key off consistently. Two structurally different modeling approaches were available: a strict hierarchical taxonomy, or a knowledge graph with typed relationships between entities and concepts.

**Decision.** A controlled taxonomy: a tree of domain → category → leaf type, defined in one YAML file (`ontology/healthcare_ontology.yaml`), loaded by a single service (`OntologyService`) that every other module goes through. A classifier may only resolve to a real leaf id in this tree — never an invented category, never free text.

**Alternatives considered.**
- **Knowledge graph** (documents, entities, and concepts as nodes with typed edges — e.g. "this contract *references* this regulation, *governs* this provider, *supersedes* that agreement"). This would capture genuinely richer relationships than a tree can — a document can be *about* several things in ways a single classification path doesn't express — and would support relationship-based queries a taxonomy can't ("show me every document that references North Valley Hospital's credentialing status").
- **No controlled vocabulary at all** — let a classifier (especially an LLM) emit whatever category label it thinks fits, and reconcile/dedupe labels later. Maximally flexible, essentially impossible to govern or audit.

**Trade-offs.** A taxonomy is simpler to build, version, and reason about, and it directly supports the two things this POC actually needs most: a fixed set of choices a human reviewer can pick from, and a fixed set of security defaults to hang off each category. It cannot express "this document is 70% about Legal and 30% about Financial," or model relationships *between* documents at all — a knowledge graph would. For a single-classification-per-document enterprise content pipeline where the primary consumers of the category are security policy and chunking-hint selection, a taxonomy's simplicity wins. A system whose core value proposition was relationship discovery across documents (compliance chains, entity resolution across contracts) would need a graph instead, likely *alongside* this taxonomy rather than replacing it.

---

## ADR-002: Hybrid classification (rules + embeddings + gated LLM) vs. any single method

**Problem.** No single classification strategy is correct at every confidence level and every cost budget (see [classification.md](classification.md) for the full discussion). Rules are cheap and explainable but brittle to paraphrase; embeddings catch paraphrase but (with a dependency-free provider) are a blunter instrument; LLMs are the most flexible but cost money, add latency, and — if not constrained — can classify outside the controlled ontology entirely.

**Decision.** Blend rule-based and embedding-based votes on every document with confidence-tiered weighting (leaning harder on the rule vote when it's already decisive), and invoke an LLM adjudication call only when the blended confidence lands in an uncertain middle band (`0.55–0.85`) *and* an LLM is actually configured — structurally constrained to the already-narrowed candidate set, never free text.

**Alternatives considered.**
- **Rules only.** Free, instant, fully explainable, zero infrastructure. Fails on any document that doesn't happen to use the ontology's own keyword vocabulary.
- **ML/embeddings only.** Better generalization than pure keyword matching, at the cost of explainability and (with a weak embedding provider) not actually being much better in practice than rules for this corpus.
- **LLM for every document.** The most capable single method, and the most expensive — cost and latency scale linearly with document volume, which is precisely the wrong shape for a pipeline meant to demonstrate a path to processing enterprise-scale (1TB-class) volume.

**Trade-offs.** The hybrid approach's cost-aware gating means most documents never reach the LLM stage at all — which is the entire point at scale — but it also means the calibration constants doing the gating (`SATURATION_K=3.5`, the `0.55–0.85` band, the `0.95` dominant-rule threshold) are hand-picked against an 18-document golden set, not statistically fitted against a large labeled sample. A production system would recalibrate these with a real held-out evaluation set (Platt scaling or similar) rather than trust hand-tuned constants at scale — this is called out directly in the `rule_based.py` and `hybrid.py` source comments, not just here.

---

## ADR-003: Type-aware chunking (structure-aware, two-factor) vs. fixed-size or pure-semantic

**Problem.** A single fixed-size chunking strategy applied uniformly across 9 file formats and 5 content domains either destroys structure that matters (splitting a table mid-row, separating a slide's title from its bullets) or ignores semantic distinctions that matter within a single format (a contract PDF and a runbook PDF need different chunk boundaries despite being "the same file type").

**Decision.** A two-factor chunker selector: file **structure** decides first, when the format itself implies a natural boundary (slide, worksheet, email) — semantics cannot override this. Ontology-configured **semantic hint** decides second, only for flowing-text formats that offer no structural hint of their own.

**Alternatives considered.**
- **Fixed-size chunking** (split every N characters/tokens, maybe with overlap). Format- and content-agnostic, trivial to implement, and the default most naive RAG pipelines actually ship with. Destroys tabular structure, breaks slides mid-thought, and treats a contract clause the same as an invoice line item.
- **Pure semantic chunking** (always chunk by document-type hint, ignore file structure). Would try to apply prose-oriented paragraph grouping to a spreadsheet, where "paragraph" isn't a meaningful unit at all — you'd either lose the header-to-row association or produce nonsensical splits.
- **Pure structure-based chunking** (always chunk by format's native unit, no semantic hint ever). Would chunk every contract, runbook, and invoice PDF identically, discarding the exact distinction ("clauses need to stay together," "code blocks stay standalone") that makes type-aware chunking worth having in the first place.

**Trade-offs.** The two-factor approach requires maintaining six chunker implementations instead of one, and requires the ontology to carry a chunking hint per category (one more thing to keep correct as the ontology grows) — real added complexity, justified only because the alternative's failure modes (broken tables, clause fragments, code split across chunks) are exactly the kind of thing that makes retrieval quietly worse without an obvious error to point at. `TechnicalDocumentChunker`'s code-block handling and `SpreadsheetChunker`'s header-repetition are both directly downstream of taking this trade-off seriously rather than chunking generically "well enough."

---

## ADR-004: Hybrid retrieval (vector + lexical + ontology + metadata) vs. vector-only or lexical-only

**Problem.** Vector (semantic) search alone misses exact-term and rare-term matches that a document happens to share verbatim with the query (a specific claim ID, a specific CPT code, a defined legal term) because embedding similarity is fundamentally approximate. Lexical (keyword) search alone misses paraphrase and topical similarity entirely.

**Decision.** Run semantic and lexical retrieval in parallel over the same ACL-and-filter-narrowed candidate set, then combine them with ontology-match and metadata-confidence signals in an explainable weighted-sum reranker (`0.45/0.25/0.20/0.10`), with every component score returned alongside the final rank rather than hidden inside a single opaque number.

**Alternatives considered.**
- **Vector-only.** The default assumption in most RAG tutorials. Simpler (one index, one score), but blind to exact-term matches and gives no natural way to weight in ontology/domain signals without folding everything into the embedding itself.
- **Lexical-only (BM25).** Excellent for exact and rare-term matches, blind to paraphrase and synonymy.
- **A single learned end-to-end reranker (e.g. a cross-encoder) with no separate weighted-sum stage.** Likely higher quality at production scale, but requires a model (with its own latency/cost/hosting story) that this POC's zero-external-dependency `DEMO_MODE` constraint doesn't allow for by default.

**Trade-offs.** The explainable weighted-sum approach is easy to reason about, easy to tune via config, and — critically for a manager-facing demo — easy to show someone *why* a result ranked where it did. It is explicitly a heuristic: the weights (`0.45/0.25/0.20/0.10`) are POC defaults, not learned or validated against a large relevance-judged query set, and the `Reranker.score()` interface is deliberately shaped so a cross-encoder model could replace the weighted sum later without any change to what feeds into it (the same semantic/lexical candidate scores would still be computed the same way upstream).

---

## ADR-005: Confidence-based human review vs. always-auto-classify or always-manual-review

**Problem.** Every automated classification is wrong sometimes. The question is what happens when it is: silently accept the guess (risking a confidently-wrong, undiscoverable misfiling), or force every document through a human (which defeats the purpose of automating classification at all).

**Decision.** Route by confidence: `AUTO_ACCEPT` (≥0.90) and `SECONDARY_VALIDATION` (0.70–0.89) continue through the pipeline automatically; anything below `0.70` halts at `REVIEW_REQUIRED` until a human approves or corrects it, with a full audit trail (`original_prediction` vs. `human_correction` vs. `reviewer` vs. `timestamp`) preserved either way.

**Alternatives considered.**
- **Always auto-classify, no review path.** Maximizes throughput, but a confidently-wrong classification is worse than an honestly-uncertain one — it's indistinguishable from a correct one until someone notices a document is missing from where they expected to find it, or present somewhere it shouldn't be.
- **Always require manual review.** Maximizes correctness at the total cost of automation's value — if every document needs a human anyway, there's no point running a classifier first.
- **A single fixed confidence cutoff** (accept above it, review below it), no middle "secondary validation" tier. Simpler, but throws away the distinction between "confident enough to skip review" and "confident enough to proceed automatically, but still worth a periodic spot-check" — the middle tier exists precisely to make that distinction visible in metrics (`cost_aware_routing` in `GET /api/metrics`) without blocking the pipeline on it.

**Trade-offs.** The three-tier threshold model (`0.90`/`0.70` cutoffs) is itself a hand-picked POC default, calibrated against the same 18-document golden set as the classifier's own constants — not derived from a cost model of what a misclassification versus a review actually costs an organization in practice. A production deployment would want those thresholds tuned against a real cost/risk trade-off (how expensive is a review-queue item vs. how expensive is a misfiled confidential document?), and would likely want per-domain thresholds rather than one global pair (a misclassified Legal contract plausibly warrants a stricter threshold than a misclassified meeting-notes memo).

---

## ADR-006: Event-driven architecture — in-process now, Kafka/Event Hub-shaped later

**Problem.** The pipeline needs to record and react to stage transitions (for observability, and eventually for scaling different stages independently), but building against a real message broker adds infrastructure this POC's zero-external-dependency goal explicitly rules out.

**Decision.** An in-process `EventBus` (`app/events/bus.py`) with the same event names and payload shapes a Kafka/Event Hub/PubSub topic would carry, dispatched synchronously via direct function calls to in-process subscribers instead of through a broker.

**Alternatives considered.**
- **A real message broker from day one** (Kafka, Event Hub, or even a lightweight one like Redis Streams). Would prove the production shape directly, at the cost of requiring an external service to run the POC at all — directly against the "runs locally with zero external services" goal this build was scoped to.
- **No event abstraction at all** — just call the next stage's function directly, with logging as an afterthought. Simpler still, but would require rewriting the orchestration logic (not just the transport) to introduce a broker later, since there'd be no seam to swap in the first place.

**Trade-offs.** The in-process bus proves the *shape* of the production design (same event vocabulary, same payloads, same "publish and let independent subscribers react" pattern) without proving its actual scaling properties — there is no backpressure, no consumer group rebalancing, no at-least-once delivery guarantee, and no dead-letter queue here, because none of those problems exist yet when `publish()` is a synchronous Python function call within a single process. The explicit bet is that swapping `publish()`'s body for a topic-produce call, and letting independent worker pools consume each stage's topic, requires no change to anything upstream of `app/events/bus.py` — but that bet is untested in this codebase, precisely because testing it would require the external broker this POC deliberately doesn't run. See [production-scaling.md](production-scaling.md) for what actually needs to be built to make that bet good.

---

## ADR-007: Dependency-free local-hash embeddings as the default provider

**Problem.** `DEMO_MODE` needs to run with zero external services and no heavyweight optional dependencies (no GPU, no multi-hundred-megabyte model download), but still needs *some* notion of semantic similarity for the embedding classifier vote and vector retrieval to function at all.

**Decision.** Default `EMBEDDING_PROVIDER=local_hash`: a dependency-free deterministic feature-hashing embedding (unigrams + bigrams hashed into a fixed-dimension vector, per Weinberger et al.) requiring no model download and no GPU/CPU-heavy inference. `sentence_transformers` (a real learned sentence embedding model) and an OpenAI-compatible embeddings API are both fully wired as alternative providers behind the same `EmbeddingProvider` interface, selected purely by config.

**Alternatives considered.**
- **`sentence_transformers` as the default.** Meaningfully better semantic representation — genuine paraphrase and synonymy capture, not just lexical-overlap-by-different-math. Pulls in `torch` (600MB+), meaningfully slows first install, and isn't guaranteed to run identically on every machine this POC might be demoed from.
- **A hosted embeddings API as the default.** Best quality, but violates the "zero external services, runs offline" constraint outright — the opposite of what `DEMO_MODE` is for.

**Trade-offs.** `local_hash` is explicit, in its own docstring, about what it is *not*: "NOT a learned semantic embedding — it is a bag-of-hashed-terms vector, so it captures lexical/keyword overlap rather than true semantic meaning." This is why `HybridClassifier` needs `EMBEDDING_CALIBRATION` to correct for a structural scale mismatch (see [classification.md](classification.md)), and why the embedding vote in practice behaves more like "a second opinion on keyword overlap, computed differently" than "a true paraphrase detector." The trade-off is fully reversible with a one-line config change (`EMBEDDING_PROVIDER=sentence_transformers`) and `requirements-optional.txt` install — nothing about the architecture assumes the weaker provider, it's simply the guaranteed-to-run default.
