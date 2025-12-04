# SQL Explain Project

A lightweight SQL explanation system that converts SQL queries into clear English descriptions using either a rule-based parser or an LLM-based generator. The project includes a minimal web UI, schema-aware semantics, and a modular design suitable for coursework and demonstrations.

---

## 1. Project Overview

This project explains SQL queries using two complementary approaches:

### **Rule-Based Explanation**
- Parses the SQL query into structured components (SELECT, FROM, JOIN, WHERE, GROUP BY, etc.)
- Produces deterministic, reproducible explanations
- Requires no GPU or machine-learning model

### **LLM-Based Explanation**
- Converts parsed SQL structure into an instruction prompt
- Uses a local seq2seq model (default: `google/flan-t5-base`) to produce fluent English descriptions
- Automatically falls back to the rule-based explanation when the LLM output is incorrect or contains SQL code

---

## 2. Folder Structure

```
project/
│
├── ui/
│   └── app_streamlit.py        # Streamlit web interface
│
├── src/
│   ├── explain.py              # Explanation engine (rule-based + LLM)
│   ├── search.py               # SQL parsing utilities
│   ├── prompt.py               # Prompt builder for LLM mode
│   ├── model.py                # Model loading and text generation
│   ├── col_semantics.py        # Column semantic guessing via LLM
│   └── __init__.py
│
├── requirements.txt
└── README.md
```

---

## 3. Installation

Clone the repository:

```bash
git clone https://github.com/YufanSongVertin/sql-explainer.git
cd sql-explainer
```

Install dependencies:

```bash
pip install -r requirements.txt
```

(Optional) select a custom model:

```bash
export SQLEXPLAIN_MODEL_NAME="google/flan-t5-large"
```

---

## 4. Running the Web UI

Launch the Streamlit application:

```bash
streamlit run ui/app_streamlit.py
```

This provides an interface to:
- Input SQL queries
- Choose rule-based, LLM, or both explanation modes
- Compare outputs interactively

---

## 5. Running from the Command Line

You can directly call the explainer:

```bash
python -m src.explain --query "SELECT name FROM users WHERE age > 25;"
```

Example result:

```
High‑level summary:
The query retrieves users older than 25.

Detailed breakdown:
- Reads from table users
- Selects the column name
- Filters rows using age > 25
```

---

## 6. Python API Usage

```python
from src.explain import explain_sql_detailed, explain_sql_with_model

query = "SELECT AVG(amount) FROM payments GROUP BY user_id;"
print(explain_sql_detailed(query))
print(explain_sql_with_model(query))
```

---

## 7. Column Semantic Reasoning

The system uses an LLM to infer likely column meanings:

```
c.customer_id → “unique identifier for each customer”
```

This improves readability, especially for large or poorly documented schemas.  
`lru_cache()` avoids recomputing repeated columns.

---

## 8. Changing the LLM Model

By default:

```
google/flan-t5-base
```

Switch model via environment variable:

```bash
export SQLEXPLAIN_MODEL_NAME="google/flan-t5-large"
```

Or modify in `model.py`:

```python
DEFAULT_MODEL_NAME = "google/flan-t5-base"
```

Any HuggingFace seq2seq transformer is supported.

---

## 9. Example SQL Query

```
SELECT DISTINCT c.customer_id, c.name, AVG(t.spend) AS avg_spend
FROM customers c
JOIN transactions t ON c.customer_id = t.customer_id
WHERE t.date >= '2024-01-01' AND t.country = 'US'
GROUP BY c.customer_id, c.name
HAVING AVG(t.spend) > 1000
ORDER BY avg_spend DESC, c.name ASC
LIMIT 10 OFFSET 5;
```

The system outputs:
- High‑level explanation
- Detailed breakdown of SELECT / JOIN / WHERE / GROUP / HAVING / ORDER / LIMIT

---

## 10. Assignment Requirement Checklist

This README includes:
- Clear project purpose
- Explanation of system design
- Instructions for installation, usage, and running the UI
- Rule-based and LLM explanation details
- Model configuration instructions
- SQL examples
- API usage documentation

This satisfies academic project documentation expectations.

---

## 11. License

MIT License (or replace according to assignment requirements).
