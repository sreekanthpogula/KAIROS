from __future__ import annotations

from typing import Iterator

from pydantic import BaseModel, Field

from app.connectors.base import BaseConnector, ConnectorDocument, ConnectorError


class HttpConfig(BaseModel):
    urls: list[str] = Field(description="Explicit list of URLs to download")
    timeout_seconds: float = Field(default=30.0, description="Per-request timeout")


class HttpConnector(BaseConnector):
    """Downloads a fixed list of URLs. The generic building block for any
    source that exposes documents over plain HTTP(S) — a public dataset, a
    signed download link, a REST API endpoint that returns a file body."""

    connector_type = "http"
    display_name = "HTTP(S) URL"
    description = "Downloads one or more explicit URLs and ingests each as a document."
    direction = "pull"

    @classmethod
    def config_schema(cls) -> dict:
        return HttpConfig.model_json_schema()

    def list_documents(self, config: dict) -> Iterator[ConnectorDocument]:
        try:
            cfg = HttpConfig.model_validate(config)
        except Exception as exc:
            raise ConnectorError(f"Invalid HTTP connector config: {exc}") from exc

        import httpx

        for url in cfg.urls:
            try:
                resp = httpx.get(url, timeout=cfg.timeout_seconds, follow_redirects=True)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise ConnectorError(f"Failed to fetch {url}: {exc}") from exc

            filename = url.rstrip("/").rsplit("/", 1)[-1] or "downloaded_file"
            content_type = resp.headers.get("content-type", "").split(";")[0].strip()
            yield ConnectorDocument(
                filename=filename,
                content=resp.content,
                source_uri=url,
                source_system="http-connector",
                metadata={"content_type": content_type, "status_code": resp.status_code},
            )
