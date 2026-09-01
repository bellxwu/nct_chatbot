# CLAUDE.md — NCT Trials Explorer

Project memory for the NCT (ClinicalTrials.gov) explorer. Read automatically by
both Cowork and Claude Code at the start of every session.

## Goal

Build an explorer that queries ClinicalTrials.gov for clinical trials and links
them to emerging biotech companies. Initial focus is **oncology** trials.

## Phases
- **Phase 1** - create a chatbot interface with Gradio and LangGraph that simply talks to the ClinicalTrials.gov REST API (v2)

- **Phase 2** - create a query tool that is able to pull the raw json files from the API and store them locally in memory such that they can be embedded and used in ChromaDB for a RAG.

- **Phase 3** — Combine all elements to query the ClinicalTrials.gov REST API (v2) and store results,
  associate trials with emerging biotech companies, and build an LLM/RAG agent
  over the collected trials (course stack — LangGraph, Chroma, MCP) that can
  answer research questions and drive a real-time dashboard.

  Core steps (retrieve-then-generate; the LLM is inside the loop, not bolted on):
  1. **Ingest** — query the ClinicalTrials.gov API and store raw trials (JSON +
     a flattened CSV/Parquet) in `all_data/`. This durable dataset is the
     foundation and is what `scripts/NCT_query.py` is meant to own (pagination,
     parsing, persistence). Associate trials with emerging biotech companies.
  2. **Embed & index** — chunk the stored trial text (eligibility, brief
     summary, outcome measures, etc.), run it through an embedding model, and
     load the vectors into Chroma. We embed the *stored trial records*, not "the
     API." This is the retrieval layer.
  3. **Choose the generation model** — the LLM that reads retrieved context and
     writes answers. Decide early since it shapes prompt/token budget, but it's
     a config choice, not a build phase.
  4. **Retrieval + agent** — the agent takes a user question, does semantic
     retrieval from Chroma ("find trials like this"), and can also call the live
     API or other connectors as tools for fresh/exact lookups ("current status
     of NCT01234567"), then passes that context to the LLM. This
     retrieve-then-generate loop *is* the RAG.
  5. **Orchestrate with LangGraph** — wire the steps (retrieve → maybe call a
     tool → generate → maybe loop) into a controllable graph. LangGraph is the
     framework the agent runs inside, not a final packaging step.

  One-liner: ingest trials → embed into Chroma → an LLM-driven agent
  (orchestrated by LangGraph) retrieves relevant trials and generates answers,
  feeding a real-time dashboard.

## Data sources

Data path is **connector-first**:

- **Primary (exploration):** the `c-trials` MCP connector (ClinicalTrials.gov
  API v2), available in Cowork. Key tools: `search_trials`, `get_trial_details`,
  `search_by_sponsor` (company pipeline / competitive intelligence),
  `search_investigators`, `analyze_endpoints`. Use this for quick discovery,
  sponsor analysis, and shaping what the pipeline needs to store.
- **Deliverable (pipeline):** `scripts/NCT_query.py` — a direct REST client
  against `https://clinicaltrials.gov/api/v2/studies`. Currently a stub; needs
  pagination, parsing, and persistence. This is the durable, reproducible
  scraper the project is ultimately building. - create a chatbot with LLMs and RAG agent over the collected trials.
- Template
- Complementary connectors available if useful: `chembl` (drug/target/
  mechanism data), `pubmed`, `biorxiv`, `open-targets`.

## Repo layout
- `config.py` — paths: `base_dir`, `data_dir` (`all_data/`), `script_dir`.
- `all_data/` — output data lands here (currently empty).
- `pyproject.toml` / `uv.lock` — deps managed with `uv`. Stack includes
  requests, pandas-adjacent tooling, sqlalchemy + psycopg2, langchain/langgraph,
  chromadb, fastmcp.
- `05_src/` / `labs/` — SEPARATE UofT "Deploying AI" course work (chat apps, MCP servers,
  RAG/embeddings labs). **Not part of the NCT project** — ignore unless asked. This acts as a template


## Conventions

- Use `uv` for dependency and environment management (`uv run`, `uv add`).
- Reference paths via `config.py` rather than hardcoding.
- Storage: no strict preference yet. Default for Phase 1 = flat files (JSON of
  raw API responses + a flattened CSV/Parquet) in `all_data/`. A relational DB
  (SQLite, or Postgres via the already-present sqlalchemy/psycopg2) is the
  natural upgrade for Phase 2 once trial↔company relationships matter.
- Oncology is the working scope for queries and examples unless stated otherwise.

## Workflow (Cowork + Code)

- **Cowork** — discovery via `c-trials`, drafting schemas, producing reports
  (xlsx/docx/pdf), scheduled scans, live artifact dashboards.
- **Claude Code** — creating the chatbot able to query NCT trials and answer questions. 
