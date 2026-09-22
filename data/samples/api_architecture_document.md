# API Architecture Document: Patient Portal Platform

## Overview

This document describes the system architecture for the Patient Portal API platform, including service boundaries, data flow, and integration points.

## System Architecture

The platform follows a service-oriented architecture with the following components:

- API Gateway (request routing, rate limiting)
- Patient Identity Service
- Appointment Scheduling Service
- Document Retrieval Service
- Notification Service

## API Design

All services expose a REST API secured via OAuth2 bearer tokens. The API design follows resource-oriented URL conventions.

```
GET /api/v1/patients/{patient_id}/appointments
POST /api/v1/appointments
```

## Authentication

Requests must include an `Authorization: Bearer <token>` header. Tokens are issued by the Identity Service and expire after sixty (60) minutes.

## Data Flow

Client requests enter through the API Gateway, are authenticated against the Identity Service, and are routed to the appropriate downstream service. Responses are cached at the gateway layer for fifteen (15) seconds where safe.
