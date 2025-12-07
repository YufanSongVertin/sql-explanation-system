# src/explain.py

import re
from typing import List, Optional

from .search import SqlQuery, parse_sql
from .prompt import build_prompt_for_sql_explanation
from .model import SqlExplainModel, SqlExplainModelConfig
from .col_semantics import describe_column_with_llm


# ---------- Column-level semantic enhancement using LLM ---------- #

def _alias_to_table(alias: str, q: SqlQuery) -> Optional[str]:
    """
    Given a table alias (e.g., 'c'), return the actual table name
    by checking the FROM/JOIN clauses.

    Returns:
        The real table name if found, otherwise None.
    """
    for t in q.tables:
        if t.alias == alias:
            return t.name
        # Handle patterns such as: FROM customers customers
        if t.name == alias and t.alias is None:
            return t.name
    return None


def _attach_column_description(expr: str, q: SqlQuery) -> str:
    """
    Attach an LLM-generated short semantic description to simple column forms:
       alias.column → alias.column (description)
    Only applies to simple expressions.

    If the expression is not a simple alias.column or if an error occurs,
    return the expression unchanged.
    """
    m = re.match(r"\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*$", expr)
    if not m:
        return expr

    alias, col = m.group(1), m.group(2)
    table_name = _alias_to_table(alias, q) or alias

    try:
        desc = describe_column_with_llm(table_name, col).strip()
        if desc:
            return f"{expr} ({desc})"
    except Exception:
        return expr

    return expr


# ---------- Rule-based explanation components ---------- #

def _describe_overall_intent(q: SqlQuery) -> str:
    """
    Describe the high-level purpose of the query.
    """
    has_agg = any(it.is_aggregate for it in q.select_items)
    has_group = bool(q.group_by)
    has_limit = q.limit is not None
    has_order = bool(q.order_by_items)

    if has_agg and has_group and has_limit and has_order:
        first_order = q.order_by_items[0]
        direction = first_order.direction
        metric = first_order.expr
        dir_word = "highest" if direction == "DESC" else "lowest"
        return (
            f"This query finds the {dir_word} {q.limit} groups based on {metric}, "
            f"aggregating rows by {', '.join(q.group_by)}."
        )

    if has_agg and has_group:
        return (
            "This query produces an aggregated report where rows are grouped "
            f"by {', '.join(q.group_by)} and aggregate metrics are computed for each group."
        )

    if has_agg and not has_group:
        return (
            "This query computes one or more aggregate metrics over the filtered rows "
            "from the underlying tables."
        )

    if q.where_clauses:
        return (
            "This query retrieves detailed rows that satisfy specific filter conditions "
            "from the underlying tables."
        )

    return "This query retrieves data from the underlying tables."


def _describe_tables(q: SqlQuery) -> str:
    """
    Describe FROM and JOIN clauses.
    """
    if not q.tables:
        return "No FROM clause was detected."

    main = []
    joins = []

    for i, t in enumerate(q.tables):
        if i == 0 and t.join_type is None:
            main.append(t)
        else:
            joins.append(t)

    parts: List[str] = []

    names = []
    for t in main:
        if t.alias:
            names.append(f"{t.name} (alias {t.alias})")
        else:
            names.append(t.name)
    if names:
        parts.append("It reads data from " + ", ".join(names) + ".")

    for t in joins:
        jt = t.join_type or "JOIN"
        desc = f"It performs a {jt} on {t.name}"
        if t.alias:
            desc += f" (alias {t.alias})"
        if t.join_condition:
            desc += f" using the join condition {t.join_condition}"
        desc += "."
        parts.append(desc)

    return " ".join(parts)


def _describe_select(q: SqlQuery) -> str:
    """
    Describe SELECT clause with semantic column annotations.
    """
    if not q.select_items:
        return "No SELECT clause was detected."

    simple: List[str] = []
    aggs: List[str] = []

    for it in q.select_items:
        raw = it.raw.strip()
        pretty_raw = _attach_column_description(raw, q)

        label = pretty_raw
        if it.alias:
            label += f" (as {it.alias})"

        if it.is_aggregate:
            aggs.append(label)
        else:
            simple.append(label)

    parts: List[str] = []
    if q.distinct:
        parts.append("The query selects DISTINCT rows.")
    if simple:
        parts.append("It includes the columns " + ", ".join(simple) + ".")
    if aggs:
        parts.append("It computes the aggregate expressions " + ", ".join(aggs) + ".")

    return " ".join(parts)


def _describe_filters(q: SqlQuery) -> str:
    """
    Describe WHERE filters.
    """
    if not q.where_clauses:
        return ""

    if len(q.where_clauses) == 1:
        return "It filters rows where " + q.where_clauses[0] + "."

    intro = "It filters rows using the following conditions:"
    bullets = "; ".join(f"[{i+1}] {cond}" for i, cond in enumerate(q.where_clauses))
    return f"{intro} {bullets}."


def _describe_group_having(q: SqlQuery) -> str:
    """
    Describe GROUP BY and HAVING.
    """
    parts: List[str] = []

    if q.group_by:
        pretty_cols = [
            _attach_column_description(col, q) for col in q.group_by
        ]
        parts.append("Rows are grouped by " + ", ".join(pretty_cols) + ".")

    if q.having:
        parts.append("Only groups satisfying the condition " + q.having + " are kept.")

    return " ".join(parts)


def _describe_order_limit(q: SqlQuery) -> str:
    """
    Describe ORDER BY and LIMIT / OFFSET.
    """
    parts: List[str] = []

    if q.order_by_items:
        orders = []
        for item in q.order_by_items:
            direction = "ascending" if item.direction == "ASC" else "descending"
            orders.append(f"{item.expr} ({direction})")
        parts.append("The results are ordered by " + ", ".join(orders) + ".")

    if q.limit is not None:
        if q.offset:
            parts.append(
                f"It skips the first {q.offset} rows and then returns at most {q.limit} rows."
            )
        else:
            parts.append(f"It returns at most {q.limit} rows.")

    return " ".join(parts)


def explain_sql_detailed(query: str) -> str:
    """
    Entry point for rule-based SQL explanation.
    """
    q = parse_sql(query)

    segments: List[str] = [
        _describe_overall_intent(q),
        _describe_tables(q),
        _describe_select(q),
    ]

    filters = _describe_filters(q)
    if filters:
        segments.append(filters)

    gh = _describe_group_having(q)
    if gh:
        segments.append(gh)

    ol = _describe_order_limit(q)
    if ol:
        segments.append(ol)

    return "\n".join(seg for seg in segments if seg)


# ---------- LLM-based explanation with silent fallback ---------- #

_model_singleton: Optional[SqlExplainModel] = None


def get_global_model() -> SqlExplainModel:
    """
    Return the global LLM instance for full-query explanation.
    """
    global _model_singleton
    if _model_singleton is None:
        _model_singleton = SqlExplainModel(SqlExplainModelConfig())
    return _model_singleton


def explain_sql_with_model(query: str, use_rule_backup: bool = True) -> str:
    """
    Use LLM to generate an explanation for the SQL query.

    Steps:
        1. Parse SQL → SqlQuery
        2. Build a natural-language prompt
        3. Run the LLM
        4. If output appears to be SQL instead of explanation → fallback

    Args:
        query: SQL query string
        use_rule_backup: whether to fall back silently to rule-based explanation

    Returns:
        A string explanation (LLM output or fallback output).
    """
    parsed = parse_sql(query)
    prompt = build_prompt_for_sql_explanation(parsed)

    try:
        model = get_global_model()
        explanation = model.generate_explanation(prompt).strip()

        looks_like_sql = (
            re.match(r"(?is)^\s*select\b", explanation)
            or " from " in explanation.lower()
            or " join " in explanation.lower()
            or re.match(r"(?is)^\s*with\b", explanation)
        )

        if looks_like_sql and use_rule_backup:
            return explain_sql_detailed(query)

        return explanation

    except Exception:
        if use_rule_backup:
            return explain_sql_detailed(query)
        else:
            raise


# ---------- CLI test entry ---------- #

if __name__ == "__main__":
    test_query = """
    SELECT DISTINCT c.customer_id, c.name, AVG(t.spend) AS avg_spend
    FROM customers c
    JOIN transactions t ON c.customer_id = t.customer_id
    WHERE t.date >= '2024-01-01' AND t.country = 'US'
    GROUP BY c.customer_id, c.name
    HAVING AVG(t.spend) > 1000
    ORDER BY avg_spend DESC, c.name ASC
    LIMIT 10 OFFSET 5;
    """

    print("=== SQL query ===")
    print(test_query)

    print("\n=== Rule-based explanation ===\n")
    print(explain_sql_detailed(test_query))

    print("\n=== LLM-based explanation ===\n")
    print(explain_sql_with_model(test_query))
