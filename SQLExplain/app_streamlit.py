# app_streamlit.py

import textwrap
import traceback

import streamlit as st

# Import explanation functions
from src.explain import explain_sql_detailed, explain_sql_with_model


st.set_page_config(
    page_title="SQL Explanation Demo",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 SQL Explanation Demo")
st.write(
    "Enter an SQL query below, choose the explanation mode, and click **Explain** to view the English interpretation."
)

# Sidebar: mode selection
with st.sidebar:
    st.header("Settings")
    mode = st.radio(
        "Explanation Mode",
        ["Rule-based", "LLM-based", "Both"],
        index=2,
    )

    st.markdown("---")
    st.caption("Tip: The LLM mode may take longer to run the first time because the model needs to load.")

# Main UI
default_sql = textwrap.dedent(
    """
    SELECT DISTINCT c.customer_id, c.name, AVG(t.spend) AS avg_spend
    FROM customers c
    JOIN transactions t ON c.customer_id = t.customer_id
    WHERE t.date >= '2024-01-01' AND t.country = 'US'
    GROUP BY c.customer_id, c.name
    HAVING AVG(t.spend) > 1000
    ORDER BY avg_spend DESC, c.name ASC
    LIMIT 10 OFFSET 5;
    """
).strip()

sql_input = st.text_area(
    "SQL Query",
    value=default_sql,
    height=220,
    help="You may replace this with your own SQL query.",
)

run_button = st.button("Explain")

if run_button:
    if not sql_input.strip():
        st.warning("Please enter an SQL query first.")
    else:
        # Rule-based explanation
        if mode in ("Rule-based", "Both"):
            st.subheader("Rule-based Explanation")
            try:
                rule_expl = explain_sql_detailed(sql_input)
                st.code(rule_expl, language="text")
            except Exception as e:
                st.error("An error occurred during rule-based explanation:")
                st.code("".join(traceback.format_exception(e)), language="text")

        # LLM-based explanation
        if mode in ("LLM-based", "Both"):
            st.subheader("LLM-based Explanation")
            with st.spinner("Generating explanation using the LLM (may take longer on first load)..."):
                try:
                    llm_expl = explain_sql_with_model(sql_input, use_rule_backup=True)
                    st.code(llm_expl, language="text")
                except Exception as e:
                    st.error("An error occurred during LLM explanation:")
                    st.code("".join(traceback.format_exception(e)), language="text")

st.markdown("---")
st.caption("SQL Explain Project · Minimal Web UI · Powered by Streamlit")
