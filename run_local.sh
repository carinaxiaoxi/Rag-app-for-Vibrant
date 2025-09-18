#!/usr/bin/env bash
set -e

python -m venv .venv
source .venv/bin/activate


pip install -U pip
pip install -r requirements.txt

python - <<'PY'
from app import config
from neo4j import GraphDatabase
try:
    GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)).verify_connectivity()
    print("Neo4j connectivity OK")
except Exception as e:
    print("Neo4j connectivity FAILED:", e)
    raise SystemExit(1)
PY

ollama pull ${EMBED_MODEL:-nomic-embed-text}

python -c "from app.neo4j_store import ensure_schema; ensure_schema()"


cat <<'MSG'
Setup complete.

MSG
