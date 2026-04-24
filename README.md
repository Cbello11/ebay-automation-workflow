# eBay Automation Workflow

This repository now includes an **all-in-one local file reader app** that can scan one file or an entire folder and summarize content.

## Supported file types
- `.txt`
- `.md`
- `.json`
- `.csv`

## Run the app
```bash
python main.py <path>
```

Examples:
```bash
python main.py README.md
python main.py .
```

## What it does
- Reads each supported file.
- Parses JSON and CSV into structured data.
- Prints concise summaries for each file.

## Run tests
```bash
python -m pytest -q
```
