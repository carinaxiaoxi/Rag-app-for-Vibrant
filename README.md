This project ingests content from [Vibrant Wellness](https://www.vibrant-wellness.com/test-menu/) into a Neo4j database, embeds it with Ollama, and allows you to query it using a retrieval-augmented generation (RAG) pipeline.


## Setup 

First run the following command:

```bash
chmod -x run_local.sh
./run_local.sh

```
If the output shows "Setup complete.", go to the next step.

## Environment Configuration

Go into .env to change the parameters, then run the following command

```bash
source .venv/bin/activate
set -a
source .env
set +a
```

## Ingest Web Content

Then, use the following command to ingest the web content

```bash
python -m app.ingest_web --url https://www.vibrant-wellness.com/test-menu/ --max-pages 80
```


## Ask Questions

Finally, use the following command to ask questions (example questions and answers are included)

```bash
python -m app.cli "What does the Wheat Zoomer Test measure?"

=== Answer ===
 The Wheat Zoomer measures immune reactivity to a wide variety of wheat proteins, including both gluten and non-gluten components, to assess wheat-related sensitivities.

```
```bash
python -m app.cli "What markers are being measured in Peanut Zoomer?"

=== Answer ===
 The Peanut Zoomer measures the following markers:
- Ara h 1 (Conarachin)
- Ara h 2 (Conglutin 7)
- Ara h 3
- Ara h 6 (Conglutin 8)
- Ara h 5 (Profilin)
- Ara h 7
- Ara h 8 & Isoform
- Ara h 9
- Ara h 10 (Oleosin 1)
- Ara h 11 (Oleosin 2)
- Ara h 12 (Defensin 1)
- Ara h 13 & Isoforms (Defensin 2 & Defensin 3)
- Glycinin
- Arachin
- Oleosin Variant A
- Oleosin Variant B

Additionally, it identifies both IgE and IgG-mediated immune responses to peanuts.

```

```bash
python -m app.cli "How do I know if I need Food Sensitivity Test or not?"

=== Answer ===
 You may need a food sensitivity test if you experience digestive discomfort, fatigue, inflammation,
chronic inflammation, digestive issues, joint pain, skin conditions, or respiratory issues.
Additionally, if you have a family history of food allergies or a history of food sensitivities, this test could be beneficial.

```



