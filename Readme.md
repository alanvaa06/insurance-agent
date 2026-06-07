# Insurance Claims Processing Agent

Automated adjudication of auto-repair insurance claims. A LangGraph workflow
parses and validates a claim, checks policy coverage, retrieves relevant policy
text (RAG over a policy PDF with ChromaDB), asks an LLM for a policy-grounded
recommendation, and produces a final decision: **Approved**, **Denied**,
**Requires review**, or **Invalid**.

## How it works

The workflow is a state machine. Mechanical steps are deterministic Python so
they are predictable, free, and unit-testable; only the two genuinely semantic
steps call the LLM.

```
parse -> validate --valid--> coverage_check -> generate_queries (LLM)
      -> retrieve_policy (RAG) -> recommend (LLM) -> price_check -> finalize -> decision
                \--invalid--> Invalid
```

| Step | Type | What it does |
|------|------|--------------|
| parse | deterministic | Normalizes claim JSON (handles several field-name schemas) |
| validate | deterministic | Required fields present, amount > 0 |
| coverage_check | deterministic | Looks up the policy in `data/coverage_data.csv` (dues, coverage window) |
| generate_queries | LLM | Builds policy search queries |
| retrieve_policy | RAG | Pulls relevant passages from the policy index |
| recommend | LLM | APPROVE / DENY grounded only in retrieved policy text |
| price_check | deterministic | Flags claims at/above `HIGH_AMOUNT_THRESHOLD` for review |
| finalize | deterministic | Combines signals into the final decision |

Decision precedence in `finalize`: coverage `NOT_COVERED` → Denied; high amount →
Requires review; recommendation DENY → Denied; otherwise → Approved.

## Prerequisites

- Python 3.11+
- An OpenAI API key
- Docker (optional)

## Setup

```bash
git clone <your-repo-url>
cd insurance-agent

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env   # then add your OPENAI_API_KEY
```

## Run

```bash
streamlit run app/main.py
```

Open http://localhost:8501. Enter a claim manually or upload a claim JSON
(see `test_cases/` for examples).

## Test

The suite runs with no network and no API key (the LLM and vector store are
faked):

```bash
pip install pytest pytest-cov
pytest
```

End-to-end tests in `tests/test_graph_routing.py` assert the five shipped test
cases produce the decisions in `test_cases/test_case_expected_results.png`.

## Configuration

All settings come from environment variables (see `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | (required) | OpenAI key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API base (override for proxies) |
| `MODEL_NAME` | `gpt-4o-mini` | Chat model |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `HIGH_AMOUNT_THRESHOLD` | `10000` | Amount that triggers manual review |
| `POLICY_PDF_PATH` | `./data/policy.pdf` | Policy document to index |
| `COVERAGE_CSV_PATH` | `./data/coverage_data.csv` | Coverage table |

## Deployment

- AWS EC2: [AWS_EC2_Deployment_Steps.md](AWS_EC2_Deployment_Steps.md)
- Docker Hub image: [Docker_HUB_TO_Instance.md](Docker_HUB_TO_Instance.md)
- Local Docker:

```bash
docker build -t insurance-agent .
docker run -p 8501:8501 --env-file .env insurance-agent
```

## Project layout

```
app/
  agent/        workflow graph, tools, coverage, prompts, state, llm factory
  database/     ChromaDB vector store
  utils/        config, logging
data/           policy.pdf, coverage_data.csv
scripts/        generate_graph.py (renders graph.png)
tests/          pytest suite
test_cases/     sample claims + expected results
```
