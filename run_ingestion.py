from pathlib import Path
from factlayer.storage import connect, initialize_schema
from factlayer.orchestrator import ingest_paths
root=Path('starter-datasets'); pdfs=list(root.rglob('*.pdf')); c=connect(); initialize_schema(c); print(ingest_paths(pdfs,c,classify=True))
