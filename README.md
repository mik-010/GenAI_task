# Claude Code Usage Analytics Platform

An end-to-end analytics platform that processes Claude Code telemetry data and delivers actionable insights through an interactive dashboard, REST API, and predictive analytics.

## Architecture

```
generate_fake_data.py  ──►  output/telemetry_logs.jsonl
                             output/employees.csv
                                    │
                        ┌───────────┘
                        ▼
              ┌─────────────────┐
              │  Ingestion      │  parser.py  →  loader.py
              │  (validate,     │  Parses JSONL batches, validates
              │   clean, load)  │  fields, upserts into PostgreSQL
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │  PostgreSQL     │  Normalized fact/dim tables
              │  (schema.sql)   │  Materialized views for fast
              │                 │  aggregation (views.sql)
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │  Query Layer    │  queries.py — shared by both
              │  (analytics)    │  dashboard and API
              └───┬─────────┬───┘
                  │         │
         ┌────────┘         └────────┐
         ▼                           ▼
┌─────────────────┐        ┌─────────────────┐
│  Dash Dashboard │        │  FastAPI Service │
│  4 pages:       │        │  /metrics/*      │
│  - Executive    │        │  /data/freshness │
│  - Engineering  │        │                  │
│  - Analyst      │        └─────────────────┘
│  - Predictions  │
└─────────────────┘
         ▲
         │
┌─────────────────┐
│  ML Module      │  Forecasting, anomaly detection,
│  (analytics.py) │  cohort variance, percentile analysis
└─────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.8+
- Docker (for PostgreSQL) or a local PostgreSQL 14+ installation

### Dependencies

All Python packages are listed in `requirements.txt`. Here is what each one does:

| Package | Role |
|---------|------|
| **Core** | |
| `psycopg2-binary` | PostgreSQL adapter for Python |
| `sqlalchemy` | SQL toolkit and ORM; provides the database engine and connection pooling |
| `pandas` | DataFrame-based data manipulation for analytics and query results |
| `python-dotenv` | Loads `.env` configuration into environment variables |
| **Dashboard** | |
| `dash` | Plotly Dash framework for building the interactive web dashboard |
| `dash-bootstrap-components` | Bootstrap-styled UI components (cards, navs, tables) |
| `plotly` | Interactive charting library used by Dash |
| **API** | |
| `fastapi` | High-performance REST API framework |
| `uvicorn[standard]` | ASGI server to run FastAPI |
| `gunicorn` | Production-grade WSGI/ASGI process manager |
| **ML / Statistics** | |
| `scikit-learn` | Machine learning utilities (used by forecasting pipeline) |
| `statsmodels` | OLS regression for cost forecasting with day-of-week seasonality |
| `scipy` | Statistical functions supporting advanced analytics |
| **Testing** | |
| `pytest` | Test framework for unit and integration tests |
| `httpx` | Async HTTP client used by FastAPI's `TestClient` |

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Generate synthetic data
```bash
# Default (30 users, 500 sessions, 30 days)
python3 generate_fake_data.py

# Realistic scale (recommended)
python3 generate_fake_data.py --num-users 100 --num-sessions 5000 --days 60
```

### 3. Start PostgreSQL
```bash
docker compose up -d
```

### 4. Ingest data
```bash
python3 -m app.ingestion.run --input-dir output
```

### 5. Launch the dashboard
```bash
python3 -m app.dashboard.app
# → http://localhost:8050
```

### 6. Launch the API (optional)
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
# → http://localhost:8000/docs
```

### 7. Run tests
```bash
python3 -m pytest tests/ -v
```

### One-command pipeline
```bash
make all   # generate → db-up → ingest → dashboard
```

## Data Generation Options

| Flag | Default | Description |
|------|---------|-------------|
| `--num-users` | 30 | Number of engineers |
| `--num-sessions` | 500 | Total coding sessions |
| `--days` | 30 | Time span in days |
| `--output-dir` | `output` | Output directory |
| `--seed` | 42 | Random seed for reproducibility |

## Output Files

| File | Format | Description |
|------|--------|-------------|
| `telemetry_logs.jsonl` | JSONL | Telemetry log batches (CloudWatch-style) |
| `employees.csv` | CSV | Employee directory |

## Database Schema

### Dimension Tables
- **employees_dim** — email, name, practice, level, location

### Fact Tables
- **events_fact** — all raw events with common attributes and JSONB payload
- **api_requests_fact** — model, tokens, cost, latency per API call
- **tool_usage_fact** — tool decisions and results with success/latency
- **api_errors_fact** — error messages, status codes, retry attempts
- **user_prompts_fact** — prompt lengths (contents redacted)

### Materialized Views
- **mv_daily_usage** — daily aggregates by practice, level, model
- **mv_hourly_peak** — request counts by day-of-week and hour
- **mv_tool_behavior** — tool accept/reject/success rates + latency percentiles
- **mv_model_efficiency** — cost/speed/tokens-per-dollar by model
- **mv_error_rates** — daily error counts by model and status code

## Dashboard Pages

### Executive Overview
- KPI cards: total requests, cost, tokens, sessions, users, avg latency
- Daily cost and token consumption trends (area + stacked charts)
- Cost breakdown by practice (donut) and seniority level (bar)
- Peak usage heatmap (day-of-week × hour)
- Model efficiency scatter (cost vs speed vs volume)

### Engineering Insights
- Tool decision frequency, success rates, and latency (log scale)
- API error timeline and breakdown by model/status
- Prompt length distribution
- Top-users leaderboard by cost

### Analyst Deep-Dive
- Multi-filter interface (practice, level, model, tool)
- Aggregated daily usage table
- CSV export of filtered data
- Tool usage timeline and session scatter plot

### Predictive Analytics
- Cost forecast with 95% confidence interval (configurable horizon)
- Cost anomaly detection (IQR method) with fence markers
- Error spike detection (z-score > 2σ)
- Token percentiles by practice (p50/p75/p90/p99)
- Cohort cost variance table (practice × level)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metrics/kpi` | GET | High-level KPI summary |
| `/metrics/usage-trends` | GET | Daily token/cost trends (filterable) |
| `/metrics/peak-times` | GET | Hourly request heatmap data |
| `/metrics/tool-behavior` | GET | Tool decision/result statistics |
| `/metrics/model-efficiency` | GET | Model cost/speed comparison |
| `/metrics/errors` | GET | Error rate summary |
| `/metrics/anomalies` | GET | Detected cost anomalies and error spikes |
| `/metrics/forecast` | GET | Cost forecast (configurable horizon) |
| `/metrics/leaderboard` | GET | Top users by cost |
| `/data/freshness` | GET | Last ingestion timestamp |

## Real-Time Capability

Start the incremental poller to tail new data appended to the JSONL file:

```bash
python3 -m app.ingestion.realtime --interval 5
```

This watches `output/telemetry_logs.jsonl` for new lines, ingests them, and refreshes materialized views automatically. The dashboard freshness indicator updates every 60 seconds.

## Design Decisions

- **PostgreSQL over NoSQL**: Chosen for SQL expressiveness, JSONB flexibility for raw attributes, materialized views for pre-computed aggregates, and strong indexing for time-range and categorical filters.
- **Materialized views for performance**: Heavy aggregations are pre-computed and refreshed after ingestion. The dashboard and API read from these views for sub-second response times.
- **Shared query layer**: A single `queries.py` module serves both Dash and FastAPI, preventing divergence between the dashboard and API.
- **Event-type-specific fact tables**: Rather than querying JSONB for every metric, typed fact tables enable efficient indexed queries on numeric columns (tokens, cost, latency).
- **Idempotent ingestion**: Employee upserts use `ON CONFLICT`, and the ingestion log tracks each run. Re-running ingestion on the same data is safe (appends new events).
- **Lightweight forecasting**: Uses OLS with day-of-week seasonality instead of heavy ARIMA/Prophet, keeping dependencies minimal while still producing meaningful predictions with confidence intervals.
- **IQR + z-score anomaly detection**: Simple, interpretable methods that work well on the data distribution without requiring model training.

## Project Structure

```
├── generate_fake_data.py       # Synthetic data generator
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # PostgreSQL container
├── Makefile                    # Convenience commands
├── .env                        # Environment configuration
├── sql/
│   ├── schema.sql              # Table definitions + indexes
│   └── views.sql               # Materialized views + refresh function
├── app/
│   ├── config.py               # Settings from environment
│   ├── db.py                   # SQLAlchemy engine
│   ├── ingestion/
│   │   ├── parser.py           # JSONL → structured event dicts
│   │   ├── loader.py           # Events → PostgreSQL tables
│   │   ├── run.py              # CLI: batch ingestion
│   │   └── realtime.py         # Incremental file-tail poller
│   ├── transform/
│   │   └── queries.py          # Shared analytics query layer
│   ├── dashboard/
│   │   ├── app.py              # Dash app entry point
│   │   └── pages/
│   │       ├── executive.py    # Executive overview page
│   │       ├── engineering.py  # Engineering insights page
│   │       ├── analyst.py      # Analyst deep-dive page
│   │       └── predictions.py  # Predictive analytics page
│   ├── api/
│   │   └── main.py             # FastAPI service
│   └── ml/
│       └── analytics.py        # Forecasting + anomaly detection
├── tests/
│   ├── test_parser.py          # Parser unit tests
│   ├── test_api.py             # API endpoint tests (mocked DB)
│   └── test_ml.py              # ML module tests (mocked queries)
└── output/                     # Generated data (gitignored)
    ├── telemetry_logs.jsonl
    └── employees.csv
```

## LLM Usage Log

I used Cursor for doing this assignment, more specifically, first thing was to use the Plan feature in Cursor to plan the steps for the assignment, and used the provided PDF document and the telemetry folder. I instructed it to read through the telemetry folder and then to start the first three points of the PDF to have a good prompt of the assignment, and simultaneously not to overload it with more points(starting from 4 in the PDF). After the planning phase, in which I chose the stack for the assignment and gathered all other necessary information not mentioned in the first prompt, I instructed it to build the project using Claude's Opus 4.6, as it is the most powerful model Claude has as of today. After all the building and running stages worked without issues, I did something the evaluator of this assignment will do after reviewing UI and not seeing any interactive issues that I thought of(giving the repo files to LLM and asking what issues it can outline). So, I used the Cursor's ask feature to ask the same question, and got some flags, 3 flags that could be outlined, and did the planning/building cycle to solve that.

## Notes

- All user identifiers in the dataset are synthetic
- Prompt contents are redacted
- Employee emails match the telemetry data
