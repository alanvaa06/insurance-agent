# Deploying to a Hugging Face Space

The live demo runs as a **Docker** Space (Hugging Face no longer accepts
`streamlit` as a direct Space SDK). It runs in demo mode, so it needs no secrets.

Live Space: https://huggingface.co/spaces/alanvaa/insurance-claims-agent

## What gets deployed

The Space contains a slim copy of the app:

- `README.md` (this folder's copy) with Docker Space frontmatter (`app_port: 8501`)
- `Dockerfile` (this folder's copy) which sets `DEMO_MODE=true`
- `requirements.txt` (this folder's copy) without `chromadb`/`openai` (unused in demo)
- `app/`, `data/`, `.streamlit/` copied from the repo root

## Steps

```bash
# 1. Authenticate (once)
hf auth login

# 2. Create the Space (Docker SDK)
hf repo create <user>/insurance-claims-agent --repo-type space --space_sdk docker --exist-ok

# 3. Stage files: copy app/, data/, .streamlit/ plus the three files in this
#    folder (README.md, Dockerfile, requirements.txt) into one directory, then:
hf upload <user>/insurance-claims-agent <staging_dir> . --repo-type space \
  --commit-message "Deploy insurance claims agent (demo mode)"
```

The Space builds the image and starts automatically. To enable live LLM mode,
add an `OPENAI_API_KEY` secret in the Space settings and remove `DEMO_MODE` (or
set it to `false`); live mode also needs `chromadb` added to `requirements.txt`.
