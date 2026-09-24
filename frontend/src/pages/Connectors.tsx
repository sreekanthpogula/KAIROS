import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import type { ConnectorCatalogEntry } from '../api/types'
import { Card, CardHeader, EmptyState } from '../components/ui/Card'
import { Pill } from '../components/ui/Badge'

const EXAMPLE_CONFIG: Record<string, string> = {
  filesystem: '{\n  "root_path": "../data/samples",\n  "glob_pattern": "*.txt",\n  "max_files": 10\n}',
  http: '{\n  "urls": ["https://example.com/document.pdf"]\n}',
  s3: '{\n  "bucket": "your-bucket-name",\n  "region_name": "us-east-1",\n  "prefix": "documents/"\n}',
  database: '{\n  "connection_string": "sqlite:///./legacy_system.db",\n  "query": "SELECT filename, body FROM attachments",\n  "filename_column": "filename",\n  "content_column": "body"\n}',
  gcs: '{\n  "bucket": "your-gcs-bucket",\n  "prefix": "documents/",\n  "credentials_json": "{\\"type\\": \\"service_account\\", ...}"\n}',
  google_drive: '{\n  "credentials_json": "{\\"type\\": \\"service_account\\", ...}",\n  "folder_id": "your-drive-folder-id"\n}',
}

export function Connectors() {
  const { data: catalog, loading } = useApi(() => api.listConnectors(), [])
  const [selected, setSelected] = useState<ConnectorCatalogEntry | null>(null)
  const [configText, setConfigText] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<{ kind: 'test' | 'run'; ok: boolean; message: string } | null>(null)

  useEffect(() => {
    if (selected && selected.direction === 'pull') {
      setConfigText(EXAMPLE_CONFIG[selected.type] ?? '{}')
      setResult(null)
    }
  }, [selected])

  async function handleTest() {
    if (!selected) return
    setBusy(true)
    setResult(null)
    try {
      const config = JSON.parse(configText)
      const res = await api.testConnector(selected.type, config)
      setResult({ kind: 'test', ok: res.ok, message: res.message })
    } catch (e) {
      setResult({ kind: 'test', ok: false, message: (e as Error).message })
    } finally {
      setBusy(false)
    }
  }

  async function handleRun() {
    if (!selected) return
    setBusy(true)
    setResult(null)
    try {
      const config = JSON.parse(configText)
      const res = await api.runConnector(selected.type, config)
      setResult({
        kind: 'run',
        ok: res.failed_documents === 0,
        message: `Job ${res.job_id.slice(0, 8)} — ${res.total_documents} document(s) submitted (${res.completed_documents} ready, ${res.review_documents} review, ${res.failed_documents} failed, ${res.duplicate_documents} duplicate).`,
      })
    } catch (e) {
      setResult({ kind: 'run', ok: false, message: (e as Error).message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Connector Catalog</h1>
        <p className="text-sm text-[var(--text-secondary)]">
          A self-contained module (<code>backend/app/connectors/</code>) with zero dependencies on the rest of KCIP — designed to be copied into any other project's ingestion pipeline.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader title="Available Connectors" subtitle={catalog ? `${catalog.length} registered` : ''} />
          {loading ? (
            <p className="p-5 text-sm text-[var(--text-muted)]">Loading…</p>
          ) : (
            <ul className="divide-y text-sm" style={{ borderColor: 'var(--border)' }}>
              {catalog?.map((entry) => (
                <li key={entry.type}>
                  <button
                    onClick={() => setSelected(entry)}
                    className="flex w-full flex-col items-start gap-1 px-4 py-3 text-left hover:bg-[var(--surface-2)]"
                    style={{ backgroundColor: selected?.type === entry.type ? 'var(--surface-2)' : undefined }}
                  >
                    <div className="flex w-full items-center justify-between">
                      <span className="font-medium">{entry.display_name}</span>
                      <Pill tone={entry.direction === 'push' ? 'warning' : 'info'}>{entry.direction}</Pill>
                    </div>
                    <span className="text-xs text-[var(--text-muted)]">{entry.description}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="lg:col-span-2">
          {!selected ? (
            <Card>
              <EmptyState title="Select a connector" description="Pick one on the left to see its config schema and run it against a real source." />
            </Card>
          ) : selected.direction === 'push' ? (
            <Card>
              <CardHeader title={selected.display_name} subtitle="Push connector — other systems call this endpoint, KCIP doesn't poll it" />
              <div className="space-y-3 p-5 text-sm">
                <p className="text-[var(--text-secondary)]">
                  Set <code>WEBHOOK_INGESTION_TOKEN</code> in the backend's environment, then any external system can push a document with:
                </p>
                <pre className="overflow-x-auto rounded-md p-3 text-xs" style={{ backgroundColor: 'var(--surface-2)' }}>
{`curl -X POST http://<backend-host>/api/connectors/webhook/ingest \\
  -H "Authorization: Bearer <WEBHOOK_INGESTION_TOKEN>" \\
  -F "file=@/path/to/document.pdf"`}
                </pre>
                <p className="text-xs text-[var(--text-muted)]">Disabled (returns 404) whenever the token isn't set — never accepts unauthenticated pushes.</p>
              </div>
            </Card>
          ) : (
            <div className="space-y-4">
              <Card>
                <CardHeader title={selected.display_name} subtitle={selected.description} />
                <div className="p-5">
                  <p className="mb-2 text-xs font-medium text-[var(--text-muted)]">Config schema</p>
                  <div className="mb-4 flex flex-wrap gap-1.5">
                    {Object.keys((selected.config_schema.properties as Record<string, unknown>) ?? {}).map((key) => {
                      const required = ((selected.config_schema.required as string[]) ?? []).includes(key)
                      return (
                        <Pill key={key} tone={required ? 'warning' : 'neutral'}>
                          {key}
                          {required ? '*' : ''}
                        </Pill>
                      )
                    })}
                  </div>

                  <label className="text-xs font-medium text-[var(--text-muted)]">Config (JSON)</label>
                  <textarea
                    value={configText}
                    onChange={(e) => setConfigText(e.target.value)}
                    rows={8}
                    className="mt-1 block w-full rounded-md border bg-transparent px-3 py-2 font-mono text-xs"
                    style={{ borderColor: 'var(--border)' }}
                  />

                  <div className="mt-3 flex gap-2">
                    <button disabled={busy} onClick={handleTest} className="rounded-lg border px-4 py-2 text-sm font-medium disabled:opacity-50" style={{ borderColor: 'var(--border)' }}>
                      Test Connection
                    </button>
                    <button disabled={busy} onClick={handleRun} className="rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50" style={{ backgroundColor: 'var(--series-1)' }}>
                      Run &amp; Ingest
                    </button>
                  </div>

                  {result && (
                    <div className="mt-4 rounded-md p-3 text-sm" style={{ backgroundColor: result.ok ? 'color-mix(in srgb, var(--status-good) 12%, transparent)' : 'color-mix(in srgb, var(--status-critical) 12%, transparent)', color: result.ok ? 'var(--status-good)' : 'var(--status-critical)' }}>
                      {result.message}
                      {result.kind === 'run' && result.ok && (
                        <>
                          {' '}
                          <Link to="/ingestion" className="underline">
                            View in Ingestion →
                          </Link>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </Card>

              <Card className="p-4 text-xs text-[var(--text-secondary)]">
                <p>
                  Portability note: this connector's entire implementation lives in one file with no imports from the rest of KCIP beyond{' '}
                  <code>app/connectors/base.py</code>. The only thing tying it to this app is <code>app/services/connector_ingestion.py</code>, which feeds its output into KCIP's own pipeline — swap that one file out and the connector works unmodified in any other project.
                </p>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
