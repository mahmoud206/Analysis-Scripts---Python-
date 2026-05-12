# Analysis Scripts

A collection of reusable Python scripts for data analysis tasks such as cleaning data, calculating business metrics, building reports, and exporting final outputs.

The goal of this repository is to keep analysis scripts simple, readable, and easy to reuse across different projects.

## Repository Structure

```text
analysis-scripts/
├── scripts/
│   └── section_reactivation_analysis.py
├── reports/
│   └── .gitkeep
├── requirements.txt
├── .gitignore
└── README.md
```

- `scripts/`: Python analysis scripts.
- `reports/`: Generated reports and output files.
- `requirements.txt`: Python dependencies required to run the scripts.
- `.gitignore`: Keeps generated files and local environment files out of Git.

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Current Scripts

### Section Reactivation Analysis

File:

```text
scripts/section_reactivation_analysis.py
```

This script analyzes product section performance over time and ranks sections by reactivation opportunity.

It calculates metrics such as:

- First 12-month average sales.
- Last 12-month average sales.
- Retention ratio.
- Decline percentage.
- Overall sales trend using linear regression.
- Recent 6-month momentum.
- 2024 and 2025 sales.
- Section status: `Healthy`, `Slow Decline`, `Strong Decline`, `Critical Decline`, or `Dead Section`.
- Reactivation score for prioritization.

## Required Input Columns

The input file must contain these columns:

```text
Date
Section
bal Qty
First_Inv_Date
Margin_%_2025
```

The script automatically strips extra spaces from column names.


