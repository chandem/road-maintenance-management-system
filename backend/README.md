# AI-RMMS Backend

FastAPI backend for the AI-Powered Road Maintenance Management System.

## Local development

cd backend
python -m uvicorn app.main:app --reload

Health check: GET /health

The backend will later connect to Supabase/PostgreSQL and expose Road, Finance, Asset, Machinery, HR, Document, and AI APIs.