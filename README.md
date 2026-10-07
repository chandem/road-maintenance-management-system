# AI-RMMS — AI-Powered Road Maintenance Management System

AI-RMMS is an **AI-first road maintenance management and decision-intelligence platform** designed to help road maintenance organizations manage infrastructure, resources, operations, documents, and decisions from one connected system.

> **AI is the intelligence layer — not an add-on.**

The platform combines structured operational data, engineering rules, historical records, and organizational documents to produce evidence-based insights, recommendations, explanations, alerts, and reports while keeping final decisions under human control.

## Vision

Build an intelligent road-maintenance office where decision-makers can ask questions in natural language and receive answers grounded in actual organizational data and documents.

AI-RMMS is intended to connect:

- Road assets and condition
- Maintenance plans and work orders
- Machinery and equipment
- Materials and inventory
- Finance and budgets
- Human resources
- Technical and administrative documents
- Historical maintenance records

## AI Capabilities

### Road Intelligence
- Road-section priority scoring
- Road ranking
- Condition analysis
- Maintenance recommendations
- Risk and priority explanations
- Future predictive maintenance capabilities

### Document Intelligence
- Document classification
- Text and table extraction
- Structured information extraction
- Document validation
- Semantic search
- Evidence-based question answering
- Report and plan analysis

### Machinery Intelligence
- Equipment utilization analysis
- Maintenance status analysis
- Failure-risk indicators
- Work-order intelligence
- Maintenance planning support

### Finance Intelligence
- Budget monitoring
- Planned vs actual expenditure analysis
- Cost summaries
- Budget-risk indicators
- Evidence-based financial explanations

### Workforce Intelligence
- Workforce and assignment visibility
- Workload analysis
- Maintenance-team insights
- Resource planning support

### AI Office Assistant
Users will be able to ask questions such as:

> Which road sections currently require the highest maintenance priority?

> What maintenance activities are planned for this fiscal year?

> Which machinery requires attention?

> How much of the maintenance budget has been utilized?

> What does the latest maintenance plan say about a particular road?

Answers should be grounded in available organizational data and documents rather than generated from assumptions.

## Engineering-First AI

AI-RMMS follows an important principle:

**Database data → Engineering/scoring engine → Evidence → AI explanation**

The LLM does not determine official engineering scores by itself.

For example, road priority can be calculated from verified factors such as:

- Recorded condition
- Active work orders
- Maintenance status
- Planning signals
- Data quality

The AI then explains the calculated result using the available evidence.

This makes the system more transparent and suitable for engineering decision support.

## Human Approval and Safety

AI-RMMS is designed as a **decision-support system**, not an autonomous authority.

AI should not independently:

- Approve expenditure
- Authorize payments
- Change official budgets
- Approve contracts
- Delete official records
- Close official work orders
- Make irreversible administrative decisions

Human officials remain responsible for final decisions.

## Core Modules

### 1. Road Asset Management
Roads, sections, chainage, condition, inspections, defects, and maintenance history.

### 2. Maintenance Operations
Maintenance plans, work orders, priorities, execution, and completion tracking.

### 3. Asset Management
Organizational assets, equipment, machinery, and maintenance status.

### 4. Machinery Management
Equipment records, maintenance activities, work orders, and operational intelligence.

### 5. Finance
Budgets, expenses, planned costs, actual costs, and financial analysis.

### 6. Human Resources
Employees, organizational structure, assignments, and workforce intelligence.

### 7. Materials
Materials, inventory, consumption, availability, and future AI-supported forecasting.

### 8. Documents
Plans, reports, letters, contracts, technical documents, spreadsheets, and other office records.

### 9. AI Intelligence Layer
AI analysis, recommendations, explanations, document intelligence, semantic search, and office assistance.

## Relationship to Existing Systems

AI-RMMS is intended to complement existing specialized systems rather than unnecessarily duplicate them.

### RAMS
**Road Asset Management System**

RAMS focuses on detailed road infrastructure, field inspection, GIS, defects, condition assessment, maintenance activities, and road asset operations.

### MMMS
**Machinery Maintenance Management System**

MMMS focuses on machinery, equipment, maintenance, work orders, and inventory.

### AI-RMMS
AI-RMMS provides the **cross-system intelligence and organizational management layer**.

The long-term architecture can connect road, machinery, finance, workforce, documents, and maintenance data so management can understand the organization as one system.

## Technology Stack

### Frontend
- React
- TypeScript
- Vite
- Tailwind CSS

### Backend
- Python
- FastAPI
- Pydantic

### Database
- PostgreSQL
- PostGIS
- pgvector

### Platform Services
- Supabase Auth
- Supabase Storage
- Vercel
- Render

### AI
- Large Language Models
- Retrieval-Augmented Generation (RAG)
- Embeddings
- Deterministic engineering scoring
- Evidence-based AI explanations

## Architecture

```text
                    AI-RMMS
                       │
             ┌─────────┴─────────┐
             │   AI Intelligence │
             └─────────┬─────────┘
                       │
      ┌────────────────┼────────────────┐
      │                │                │
   Structured       Documents        Historical
      Data             │                Data
      │           RAG / Search          │
      └────────────────┼────────────────┘
                       │
       ┌───────────────┼────────────────┐
       │               │                │
     Roads          Machinery        Finance
       │               │                │
    Maintenance     Workforce       Materials
```

## Development Status

AI-RMMS is under active development.

Current foundation includes:

- Project architecture
- Development roadmap
- Database foundation
- Organization authorization foundation
- FastAPI backend foundation
- Authentication-aware API dependencies
- Road API
- Road-section API
- Maintenance-plan API
- Work-order API
- Initial AI road-priority analysis
- Evidence-based AI road explanation
- OpenAI Python SDK integration

### Current AI Feature

The first AI capability analyzes an individual road section using recorded engineering data and produces:

- Priority score
- Priority level
- Reasons
- Evidence
- Confidence
- AI explanation
- Recommended action

## Roadmap

### Phase 1 — Foundation
- Project architecture
- Authentication
- Authorization
- Database foundation
- Backend API foundation

### Phase 2 — Data Foundation
- Roads
- Road sections
- Maintenance plans
- Work orders
- Machinery
- Assets
- Employees
- Finance
- Documents

### Phase 3 — AI Core
- Engineering scoring
- AI explanations
- AI road ranking
- Recommendation engine
- AI confidence and evidence

### Phase 4 — Document Intelligence
- Document ingestion
- Classification
- Extraction
- Validation
- Embeddings
- Semantic search
- RAG

### Phase 5 — Operational Intelligence
- Maintenance intelligence
- Machinery intelligence
- Finance intelligence
- Workforce intelligence
- Alerts
- Management dashboards

### Phase 6 — Predictive Intelligence
- Failure-risk prediction
- Maintenance forecasting
- Budget forecasting
- Resource forecasting
- Advanced decision support

## Design Principles

1. **AI-first** — intelligence is built into the platform from the beginning.
2. **Evidence-based** — AI answers should be grounded in available data.
3. **Engineering-controlled** — deterministic calculations control official scores.
4. **Human-in-the-loop** — important decisions require human approval.
5. **Transparent** — recommendations should show reasons and evidence.
6. **Modular** — road, machinery, finance, HR, materials, and documents can evolve independently.
7. **Integration-ready** — designed to work with existing specialized systems.
8. **Scalable** — architecture should support multiple organizations and larger datasets.

## Repository Structure

```text
road-maintenance-management-system/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   └── schemas/
│   ├── requirements.txt
│   └── README.md
├── database/
│   ├── migrations/
│   └── seed/
├── frontend/
│   └── README.md
├── docs/
│   ├── architecture.md
│   └── development-roadmap.md
└── README.md
```

## Long-Term Goal

The long-term goal is to create an **AI-powered operating system for road maintenance organizations** where operational data and organizational documents become a continuously usable source of engineering and management intelligence.

AI-RMMS is not intended to replace engineers or managers.

**It is intended to help them make better decisions, faster, using the evidence already available in their organization.**
