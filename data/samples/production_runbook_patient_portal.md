# Production Runbook: Patient Portal API

## Service Overview

This runbook covers on-call procedures for the Patient Portal API platform.

## On-call Escalation

- Primary on-call: Platform Engineering (PagerDuty rotation)
- Secondary escalation: Engineering Manager after 15 minutes unacknowledged
- Executive escalation: VP Engineering after 60 minutes for Sev1 incidents

## Incident Response Steps

1. Acknowledge the page and open the incident channel.
2. Check the API Gateway dashboard for elevated error rates.
3. Check the Identity Service health endpoint.
4. If the Identity Service is degraded, follow the Rollback Procedure below.

## Rollback Procedure

Roll back to the previous stable deployment using the deployment pipeline's "Rollback" action. Verify health checks pass before closing the incident.

## Troubleshooting

- 401 error spikes: check for expired signing keys in the Identity Service.
- 504 timeouts: check downstream Document Retrieval Service latency.
- Known issue: cache invalidation lag can cause stale appointment data for up to 15 seconds.
