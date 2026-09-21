Veridian AI — Internal IT Support Agent

Agentic AI assistant for Veridian Corp employees to resolve IT issues using company policies, ask clarifying questions, escalate complex/risky requests, create tickets, and maintain an audit trail.

✨ Features

🤖 Natural-language IT support

📚 Policy-grounded RAG using TF-IDF + cosine similarity

🧠 LangGraph agent workflow

🎫 Automatic ticket creation for escalations

🔎 Audit trail for agent actions

📋 Knowledge Base and Employee Requests views

🔐 Gemini API integration with environment-based secrets

🔄 Agent Workflow

Employee Request
      ↓
Understand Request
      ↓
Retrieve Policy
      ↓
Reason
      ↓
Decision
 ┌────┼────────────┐
 ↓    ↓            ↓
Resolve Clarify  Escalate
                    ↓
                  Ticket
                    ↓
                Audit Log

🏗️ Tech Stack

Frontend: Streamlit

Backend: FastAPI + Uvicorn

AI: Google Gemini + LangGraph

RAG: Scikit-learn TF-IDF + cosine similarity

Database: SQLite

Testing: Pytest

Deployment: Vercel + Streamlit Community Cloud

📁 Project Structure

AIONOS_Assignment/
├── api/
│   └── index.py
├── backend/
│   ├── agents/
│   ├── rag/
│   ├── database/
│   └── main.py
├── frontend/
│   └── app.py
├── data/
│   ├── policies.json
│   ├── employee_requests.json
│   └── tickets.json
├── tests/
├── requirements.txt
├── requirements-dev.txt
└── README.md

🚀 Run Locally

git clone https://github.com/esha2005/AIONOS_Assignment.git
cd AIONOS_Assignment

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

Create .env:

GEMINI_API_KEY=your_api_key_here

Start backend:

python -m uvicorn backend.main:app --reload --port 8000

Start frontend in another terminal:

streamlit run frontend/app.py

🔌 API

Endpoint

Purpose

GET /health

Health check

GET /docs

Swagger documentation

POST /retrieve-policy

Policy retrieval

GET /tickets

Ticket list

GET /audit-logs

Audit records

☁️ Deployment

Backend: Vercel
https://aionos-assignment-2.vercel.app

Frontend: Streamlit Community Cloud

The frontend uses the BACKEND_URL Streamlit secret to connect to the deployed FastAPI backend.

🧪 Testing

pytest

Current status: 28/28 tests passing.

🎯 Assignment Objective

This project demonstrates an internal service agent capable of:

Understanding employee requests

Finding relevant company policies

Resolving simple issues

Asking for missing information

Escalating risky or unclear requests

Creating structured tickets

Maintaining an audit trail
