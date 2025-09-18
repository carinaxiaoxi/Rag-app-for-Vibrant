This project ingests content from [Vibrant Wellness](https://www.vibrant-wellness.com/test-menu/) into a Neo4j database, embeds it with Ollama, and allows you to query it using a retrieval-augmented generation (RAG) pipeline.


## Setup 

first run the following coomand

```bash
chmod -x run_local.sh
./run_local.sh

```
if the output shows "Setup complete.", go to the next step.

## Environment Configuration

go into .env to change the parameters, then run the following command

```bash
source .venv/bin/activate
set -a
source .env
set +a
```

## Ingest Web Content

then use the following command to ingest the web content

```bash
python -m app.ingest_web --url https://www.vibrant-wellness.com/test-menu/ --max-pages 80
```


## Ask Questions

finally use the following command to ask questions

```bash
python -m app.cli "What does the Wheat Zoomer Test measure?"
```



