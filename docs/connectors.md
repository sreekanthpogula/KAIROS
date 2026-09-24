# Connector Catalog

A small, deliberately self-contained module for pulling documents into KCIP
from external systems instead of relying on manual upload — and, just as
importantly, designed so it can be lifted out of KCIP entirely and dropped
into a different project's ingestion pipeline with minimal changes.

## The seven connectors

| Connector | Direction | Source shape |
|---|---|---|
| Local Filesystem | pull | A local or mounted directory (network share, synced cloud folder, container volume) |
| HTTP(S) URL | pull | Any URL that returns a downloadable file body |
| S3-Compatible Object Storage | pull | AWS S3, MinIO, Cloudflare R2, or any S3-compatible endpoint |
| SQL Database | pull | Any SQLAlchemy-supported database — the common shape for legacy systems that store attachments/blobs in a table |
| Google Cloud Storage | pull | A GCS bucket (optionally scoped to a prefix) via a service-account key |
| Google Drive | pull | A Drive folder or search query, via a service-account key — exports native Google Docs/Sheets/Slides to plain text/CSV automatically |
| Webhook | push | An inbound endpoint other systems POST documents to, instead of KCIP polling them |

Backed by real, automated tests for every one (`backend/tests/test_connectors_*.py`)
— the S3 connector against a mocked AWS S3 (`moto`), the HTTP connector
against a real local test server, the database connector against a
throwaway SQLite fixture standing in for "some other system's table", the
two Google connectors against `google-cloud-storage`/`google-api-python-client`
mocked at their source modules (no moto-equivalent exists for GCS, and no
real GCP project/credentials are available in this environment), and the
webhook connector's auth logic at the HTTP layer.

## Why Google connectors, specifically

Google's own enterprise search product, Vertex AI Search, is built around
the idea of a "data store": you point it at a source (a GCS bucket, a
Drive folder, a website, a BigQuery table) via a pre-built connector, and
it handles the pull/sync so the rest of the search pipeline never has to
know where a document originally lived. `GcsConnector` and
`GoogleDriveConnector` mirror that shape at POC scope — same idea (a
narrow, source-specific adapter that yields a uniform document shape),
without the managed sync scheduling, incremental crawling, or OAuth
consent flows a production data store would add. It's the same reason
this catalog exists at all: to demonstrate that KCIP's ingestion boundary
is a `ConnectorDocument`, not a filesystem path, so wiring in any real
data store (Google's or otherwise) is additive, not a rewrite.

## Why this is structured the way it is

`backend/app/connectors/` has **zero imports from the rest of KCIP**. Its
only third-party dependencies are generic libraries any Python project
might already use (`httpx`, `boto3`, `sqlalchemy`-core) — nothing here
knows about KCIP's database models, FastAPI app, or pipeline. The
interface each connector implements is four fields wide:

```python
@dataclass
class ConnectorDocument:
    filename: str
    content: bytes
    source_uri: str
    source_system: str
    metadata: dict[str, Any] = field(default_factory=dict)
```

That's the entire boundary. A connector's `list_documents(config)` yields
these; nothing downstream needs to know which connector produced them.

## How to actually reuse this in another project

1. Copy `backend/app/connectors/` into the other project (as a package,
   e.g. `myproject/connectors/`).
2. Keep `base.py` as-is — it has no KCIP-specific code to strip out.
3. Write your own glue, the equivalent of KCIP's
   `backend/app/services/connector_ingestion.py` (which is intentionally
   *not* part of the portable package — it's the one file that imports
   both the connector interface and KCIP's `PipelineOrchestrator`). Yours
   will call `connector.list_documents(config)` the same way and feed the
   resulting `ConnectorDocument`s into whatever your project's own
   ingestion entrypoint is.
4. If your project doesn't need one of the pull connectors, delete
   that file and remove it from `registry.py`'s `PULL_CONNECTOR_CLASSES`
   list — each connector file is fully independent of the others.

## Adding another connector

Implement `BaseConnector`: a `config_schema()` classmethod (return a
Pydantic model's `.model_json_schema()`), and `list_documents(config)` as
a generator that validates `config` against your own Pydantic model and
raises `ConnectorError` (not a raw exception) on any failure. Register it
in `registry.py`'s `PULL_CONNECTOR_CLASSES` list — the catalog API,
config-schema introspection, and the frontend's generic run/test UI all
pick it up automatically with no other changes.

## API surface

- `GET /api/connectors` — catalog: type, display name, description,
  direction, and JSON-schema config for every registered connector.
- `POST /api/connectors/{type}/test` — best-effort reachability/config
  check without a full pull.
- `POST /api/connectors/{type}/run` — pulls every document the connector
  finds and runs each through the exact same pipeline a manual upload
  goes through (creates a real `IngestionJob`, visible at
  `GET /api/ingestion/jobs/{id}` same as any other batch).
- `POST /api/connectors/webhook/ingest` — the push connector. Requires
  `WEBHOOK_INGESTION_TOKEN` to be set (bearer auth); returns 404 if unset
  rather than accepting unauthenticated pushes.

## What this deliberately doesn't do

No OAuth flows, no credential vaulting, no scheduled/polling ingestion,
no per-tenant connector configs stored anywhere — a real product would
need all of that. This catalog demonstrates the *shape* (a clean,
narrow, testable interface with a catalog/registry in front of it) at
POC scope, the same way the rest of KCIP demonstrates its architecture at
POC scope rather than production scale.
