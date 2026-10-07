# AI-RMMS Architecture

## Purpose

AI-RMMS (AI-Powered Road Maintenance Management System) is an office-wide intelligence platform for road maintenance organizations.

The system is designed to integrate existing operational systems such as:

- RAMS — Road Asset Management System
- MMMS — Machinery Maintenance Management System

It adds intelligence across road maintenance, finance, assets, machinery, human resources, documents, and operational data.

## Core Principle

AI is the intelligence layer, not a separate chatbot module.

AI-RMMS should be able to:

1. Understand structured operational data.
2. Understand organizational documents.
3. Connect information across modules.
4. Detect anomalies and risks.
5. Generate recommendations.
6. Forecast operational needs.
7. Generate reports and summaries.
8. Assist staff through natural-language interaction.

## Initial Domains

- Road Assets
- Maintenance Operations
- Machinery
- General Asset Management
- Human Resources
- Finance
- Materials and Inventory
- Documents and Knowledge
- AI Intelligence

## System Architecture

```text
                    AI-RMMS
                       |
                AI Intelligence
                       |
        +--------------+--------------+
        |              |              |
   Structured Data   Documents     External Systems
        |              |              |
   PostgreSQL       RAG/Vector       RAMS/MMMS
   + PostGIS         Search
        |              |              |
        +--------------+--------------+
                       |
              Recommendations
              Alerts / Forecasts
              Reports / Assistant
```

## Technology Direction

### Frontend
- React
- TypeScript
- Vite
- Tailwind CSS

### Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic

### Data
- PostgreSQL
- PostGIS
- pgvector

### Platform
- Supabase
- Render
- Vercel

### AI
- LLM API
- Embeddings
- Retrieval-Augmented Generation (RAG)
- Tool/function calling

## Repository Structure

```text
road-maintenance-management-system/
├── frontend/
├── backend/
├── database/
│   ├── migrations/
│   └── seed/
├── docs/
├── .env.example
├── render.yaml
└── README.md
```

## AI Governance

AI may:

- analyze
- summarize
- recommend
- forecast
- classify
- detect anomalies
- draft reports

AI must not independently:

- approve expenditure
- approve contracts
- authorize payments
- change approved budgets
- delete official records
- close official work orders

Human approval remains required for consequential operational and financial decisions.

## Development Strategy

The project will be implemented incrementally:

1. Architecture foundation
2. Database foundation
3. Authentication and organization
4. AI core
5. Document intelligence and RAG
6. RAMS integration
7. MMMS integration
8. Finance and HR
9. AI recommendations and alerts
10. Forecasting and advanced intelligence
