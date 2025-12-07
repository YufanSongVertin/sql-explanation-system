# src/prompt.py

from textwrap import dedent
from typing import List
from .search import SqlQuery, SelectItem, TableRef, OrderItem


def format_select_items(items: List[SelectItem]) -> str:
    """
    Format SELECT items for inclusion in the prompt.
    """
    if not items:
        return "None"

    lines = []
    for it in items:
        line = f"- expression: {it.raw}"
        if it.alias:
            line += f", alias: {it.alias}"
        if it.is_aggregate:
            line += f", aggregate: {it.agg_func}"
        lines.append(line)
    return "\n".join(lines)


def format_tables(tables: List[TableRef]) -> str:
    """
    Format FROM/JOIN table references for the prompt.
    """
    if not tables:
        return "None"

    lines = []
    for i, t in enumerate(tables):
        if i == 0 and t.join_type is None:
            role = "main table"
        else:
            role = t.join_type or "JOIN"
        line = f"- role: {role}, name: {t.name}"
        if t.alias:
            line += f", alias: {t.alias}"
        if t.join_condition:
            line += f", condition: {t.join_condition}"
        lines.append(line)
    return "\n".join(lines)


def format_order_items(items: List[OrderItem]) -> str:
    """
    Format ORDER BY items for the prompt.
    """
    if not items:
        return "None"
    return "\n".join(f"- {it.expr} ({it.direction})" for it in items)


def format_where_clauses(clauses: List[str]) -> str:
    """
    Format WHERE conditions for the prompt.
    """
    if not clauses:
        return "None"
    return "\n".join(f"- condition {i}: {cond}" for i, cond in enumerate(clauses, start=1))


def build_prompt_for_sql_explanation(parsed: SqlQuery) -> str:
    """
    Convert a structured SqlQuery object into a clean English prompt.
    The prompt explicitly instructs the LLM to produce only English explanations
    and avoid outputting SQL code.
    """

    distinct_str = "yes" if parsed.distinct else "no"
    group_by_str = ", ".join(parsed.group_by) if parsed.group_by else "None"

    where_block = format_where_clauses(parsed.where_clauses)
    select_block = format_select_items(parsed.select_items)
    table_block = format_tables(parsed.tables)
    order_block = format_order_items(parsed.order_by_items)

    having_str = parsed.having or "None"
    limit_str = "None" if parsed.limit is None else str(parsed.limit)
    offset_str = "None" if parsed.offset is None else str(parsed.offset)

    prompt = f"""
    You are an expert data engineer and SQL instructor.

    TASK:
    Explain in plain English what the SQL query does.
    Your explanation must be fully natural language, without ANY SQL keywords.
    Do NOT output SQL code.
    Do NOT rewrite or modify the query.
    Do NOT include backticks, code blocks, or anything resembling SQL syntax.

    SQL QUERY (for your reference only):

    {parsed.raw.strip()}

    STRUCTURED PARSE INFORMATION:

    - DISTINCT: {distinct_str}

    - SELECT items:
    {select_block}

    - FROM / JOIN tables:
    {table_block}

    - WHERE conditions:
    {where_block}

    - GROUP BY columns:
    {group_by_str}

    - HAVING condition:
    {having_str}

    - ORDER BY:
    {order_block}

    - LIMIT: {limit_str}
    - OFFSET: {offset_str}

    REQUIRED OUTPUT FORMAT (ENGLISH ONLY):

    1. A 2–3 sentence high-level summary explaining the main purpose of the query.
    2. A clear bullet-point breakdown covering:
       - Which tables are used and how they are joined
       - How rows are filtered (WHERE)
       - How rows are grouped or aggregated (GROUP BY / HAVING)
       - How results are ordered and limited (ORDER BY / LIMIT)

    IMPORTANT RESTRICTIONS:
    - Do NOT include SQL keywords (e.g., SELECT, FROM, JOIN).
    - Do NOT restate or paraphrase SQL code.
    - Do NOT include code blocks or triple backticks.
    - Write as if explaining to a business analyst with no SQL experience.
    """

    return dedent(prompt).strip()
