# Security Architecture

## The model

Every `Document` and every `Chunk` carries two security fields:

- **`security_level`** — one of `public` / `internal` / `confidential` / `restricted` (`SecurityLevel` enum, `app/core/enums.py`), with an explicit rank order (`SECURITY_LEVEL_RANK`) available for any future "at least this level" comparison logic.
- **`allowed_groups`** — a list of group names (`employee`, `legal`, `provider-management`, `finance`, `clinical`, `engineering`, `executive` — `Settings.available_groups`) that may access the document/chunk. An empty list means unrestricted (open to any requester group).

Chunks carry their own copy of both fields rather than looking them up from the parent document at query time (`Chunk.security_level`, `Chunk.allowed_groups` — denormalized alongside `document_type`/`domain`/`ontology_id` at chunk-creation time). This is the same denormalization principle used for classification metadata generally: **retrieval and ACL filtering should never need a join to reconstruct the full picture**, because a join on every query is exactly the kind of cost that stops scaling gracefully once the chunk table is large.

## Where the values come from: ontology config, not code

Security defaults are **derived from the ontology domain's configuration at classification time**, not decided by any bespoke logic in the pipeline or the API layer:

```yaml
# ontology/healthcare_ontology.yaml
domains:
  - id: financial
    name: Financial
    default_security_level: confidential
    default_allowed_groups: [finance, executive, provider-management]
```

`OntologyService.security_defaults_for(ontology_id)` walks up from whatever leaf a document was classified into, to its category, to its domain, and returns that domain's configured `default_security_level`/`default_allowed_groups` (categories and leaves inherit their domain's values unless a category or leaf overrides them — none currently do, so today this is effectively a per-domain policy, by design of the current ontology file, not a limitation of the mechanism). `PipelineOrchestrator._stage_classify` calls this immediately after a document is mapped to an ontology id, and stamps the result onto the `Document` row (which then propagates onto every `Chunk` created from it during chunking):

```python
if output.ontology_id:
    level, groups = self.ontology.security_defaults_for(output.ontology_id)
    doc.security_level = level
    doc.allowed_groups = groups
```

**This is the deliberate design point**, called out directly in the ontology YAML's own header comment and worth restating here: *security policy lives in ontology config, not scattered in code.* Changing what security level a category of document should carry is a YAML edit and a re-classification, not a hunt through application code for every place that might have hard-coded a security rule for "financial documents." A human correcting a misclassification during review gets the same treatment — `ReviewService.correct()` re-derives `security_level`/`allowed_groups` from whatever ontology id the reviewer corrected *to*, so a corrected document's access policy is never left stale from its original (wrong) classification.

Newly-received documents default to `Settings.default_security_level` (`internal`) and `allowed_groups=["employee"]` until classification actually resolves an ontology id and overwrites both — a document is never left with no access policy at all, even in the brief window between `RECEIVED` and `ONTOLOGY_MAPPED`.

## Enforcement: filtered before scoring, not after

`RetrievalService.search()` applies the ACL check as its own explicit step, before vector or lexical scoring ever runs:

```python
allowed = [c for c in candidates if self._is_allowed(c, requester_group)]
excluded_by_acl = total_candidates - len(allowed)
```

This ordering matters. An excluded chunk never enters the semantic or lexical scoring pool at all — it can't coincidentally rank well and leak through. `excluded_by_acl` is still reported back in the response (`RetrievalResult.excluded_by_acl`), so a caller (or a manager watching the demo) can see that access control actually removed something, rather than access control being invisible plumbing.

## The ACL demo scenario

This is the concrete, manually-verified demonstration of the model actually working end-to-end, and it's also the scenario that surfaced the retrieval bug documented in [retrieval.md](retrieval.md):

An "engineering" group user asks *"What are the provider termination requirements?"* — a question whose genuinely relevant content lives entirely in `legal.contracts.provider_agreement` chunks, which carry `allowed_groups: [legal, provider-management, executive]`. None of those groups is `engineering`, so every relevant chunk is excluded by the ACL filter before scoring. What's left in the candidate pool is only content the engineering group *can* see — technical architecture docs, runbooks, and so on — none of which has anything to do with provider termination.

The correct behavior is for the system to say so plainly: *"No documents you have access to contain information relevant to this question (some documents were excluded because they are outside your access level)."* Getting there reliably required the lexical-scoring fix described in [retrieval.md](retrieval.md) — without it, a coincidental weak match among the leftover technical content could get rescaled up to a false, confident-looking score, and the RAG layer would have synthesized a plausible-sounding but hallucinated answer from irrelevant content instead of admitting it had nothing relevant to say. With the fix and the `MIN_RELEVANT_SCORE = 0.30` floor in place, this was manually tested via real HTTP calls and confirmed to behave correctly (`TODO.md`, Phase 6).

## What this model does and doesn't cover

This is a POC-scoped access control model, not a production authorization system:

- **Group membership itself is a request parameter** (`requester_group`), not derived from a real identity provider, JWT claims, or session — there's no authentication layer in front of it. A production deployment would resolve the caller's actual group memberships from an IdP/SSO token before this logic ever runs.
- **Group check is a single membership test**, not a hierarchy or a policy engine — there's no concept of "finance-manager inherits finance's access plus more," for example, though `SECURITY_LEVEL_RANK`'s ordering leaves room for that kind of comparison to be added later.
- **No row-level encryption or field-level redaction** — a chunk a group can't see is excluded from results entirely, but there's no partial-redaction concept (e.g. showing a document's existence without its content).
- **No audit log of access denials** specifically (though every retrieval's `excluded_by_acl` count and the underlying `RetrievalLog` schema exist and could be extended to log *which* groups were denied *what*, for compliance reporting).

See [production-scaling.md](production-scaling.md)'s Production Readiness Scorecard for the named next steps on each of these.
