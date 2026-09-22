import { useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import { Card, CardHeader, EmptyState } from '../components/ui/Card'
import { UploadDropzone } from '../components/UploadDropzone'
import { PipelineStages } from '../components/PipelineStages'
import { Pill } from '../components/ui/Badge'

export function Ingestion() {
  const { data: jobs, loading, refetch } = useApi(() => api.listJobs(), [])
  const [selectedJob, setSelectedJob] = useState<string | null>(null)
  const { data: jobDetail } = useApi(() => (selectedJob ? api.getJob(selectedJob) : Promise.resolve(null)), [selectedJob])

  const latestJob = jobs?.[0]

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Ingestion</h1>
        <p className="text-sm text-[var(--text-secondary)]">
          detect → extract → classify → map ontology → enrich → segment → chunk → embed → index → ready
        </p>
      </div>

      <UploadDropzone onUploaded={refetch} />

      <Card>
        <CardHeader title="Pipeline Stages" subtitle={latestJob ? `Most recent document in job ${latestJob.id.slice(0, 8)}` : 'Upload a document to see it move through the pipeline'} />
        <div className="p-5">
          <PipelineStages currentStatus={jobDetail?.documents[0]?.status ?? (latestJob ? 'READY' : undefined)} />
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader title="Ingestion Jobs" subtitle="Each upload — or the batch seed script — creates one job" />
          {loading ? (
            <p className="p-5 text-sm text-[var(--text-muted)]">Loading…</p>
          ) : !jobs?.length ? (
            <EmptyState title="No jobs yet" />
          ) : (
            <ul className="max-h-[420px] divide-y overflow-y-auto text-sm" style={{ borderColor: 'var(--border)' }}>
              {jobs.map((j) => (
                <li key={j.id}>
                  <button onClick={() => setSelectedJob(j.id)} className="flex w-full items-center justify-between px-5 py-3 text-left hover:bg-[var(--surface-2)]" style={{ backgroundColor: selectedJob === j.id ? 'var(--surface-2)' : undefined }}>
                    <div>
                      <p className="font-medium">{j.job_type}</p>
                      <p className="text-xs text-[var(--text-muted)]">{new Date(j.started_at).toLocaleString()}</p>
                    </div>
                    <div className="text-right text-xs">
                      <p>{j.completed_documents}/{j.total_documents} ready</p>
                      {j.avg_processing_seconds != null && <p className="text-[var(--text-muted)]">{j.avg_processing_seconds.toFixed(2)}s/doc</p>}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader title="Job Detail" subtitle={selectedJob ? `Job ${selectedJob.slice(0, 8)}` : 'Select a job'} />
          {!jobDetail ? (
            <EmptyState title="No job selected" description="Click a job on the left to see its documents and event log." />
          ) : (
            <div className="p-5">
              <div className="mb-4 flex flex-wrap gap-2">
                <Pill tone="good">{jobDetail.completed_documents} completed</Pill>
                <Pill tone="warning">{jobDetail.review_documents} review</Pill>
                <Pill tone="critical">{jobDetail.failed_documents} failed</Pill>
                <Pill>{jobDetail.duplicate_documents} duplicate</Pill>
              </div>
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-[var(--text-muted)]">
                    <th className="py-1.5 font-medium">Document</th>
                    <th className="py-1.5 font-medium">Status</th>
                    <th className="py-1.5 font-medium">Confidence</th>
                    <th className="py-1.5 font-medium">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {jobDetail.documents.map((d) => (
                    <tr key={d.id} className="border-t" style={{ borderColor: 'var(--border)' }}>
                      <td className="py-1.5">{d.filename}</td>
                      <td className="py-1.5">{d.status}</td>
                      <td className="py-1.5">{d.confidence != null ? `${(d.confidence * 100).toFixed(0)}%` : '—'}</td>
                      <td className="py-1.5 text-[var(--status-critical)]">{d.error_message ?? ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
