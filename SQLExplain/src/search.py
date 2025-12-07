# src/search.py

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ---------- Data structures (lightweight SQL AST) ---------- #


@dataclass
class SelectItem:
    raw: str                       # Original expression, e.g. "AVG(t.spend) AS avg_spend"
    alias: Optional[str] = None    # Alias, if present
    is_aggregate: bool = False     # Whether this is an aggregate expression
    agg_func: Optional[str] = None # Aggregate function name (SUM / AVG / COUNT / ...)


@dataclass
class TableRef:
    name: str                      # Table name
    alias: Optional[str] = None    # Table alias
    join_type: Optional[str] = None        # "INNER JOIN" / "LEFT JOIN" / ...
    join_condition: Optional[str] = None   # ON condition (raw string)


@dataclass
class OrderItem:
    expr: str                      # Sort expression
    direction: str = "ASC"         # "ASC" or "DESC"


@dataclass
class SqlQuery:
    raw: str                       # Original SQL text

    distinct: bool = False
    select_items: List[SelectItem] = field(default_factory=list)

    tables: List[TableRef] = field(default_factory=list)

    where: Optional[str] = None
    where_clauses: List[str] = field(default_factory=list)  # Split into AND-clauses

    group_by: List[str] = field(default_factory=list)
    having: Optional[str] = None

    order_by_items: List[OrderItem] = field(default_factory=list)

    limit: Optional[int] = None
    offset: Optional[int] = None


# ---------- Helper functions ---------- #


def _split_clause(query: str, start_kw: str, next_kws: List[str]) -> Optional[str]:
    """
    Extract the content of a clause starting at `start_kw` up to the next keyword
    in `next_kws` (or the end of the query if none is found).

    Example:
        _split_clause(sql, "where", ["group by", "order by", "limit"])
    """
    q_lower = query.lower()
    start_idx = q_lower.find(start_kw)
    if start_idx == -1:
        return None

    content_start = start_idx + len(start_kw)

    next_positions: List[int] = []
    for kw in next_kws:
        pos = q_lower.find(kw, content_start)
        if pos != -1:
            next_positions.append(pos)

    if next_positions:
        end_idx = min(next_positions)
        content = query[content_start:end_idx]
    else:
        content = query[content_start:]

    return content.strip() or None


def _parse_select_clause(select_clause: str) -> (bool, List[SelectItem]):
    """
    Parse the SELECT clause.

    Responsibilities:
      - Detect DISTINCT
      - Split by commas into individual expressions
      - Detect aggregate functions and aliases
    """
    distinct = False
    if not select_clause:
        return distinct, []

    clause = select_clause.strip()

    # DISTINCT
    if clause.lower().startswith("distinct "):
        distinct = True
        clause = clause[len("distinct "):]

    parts = [p.strip() for p in clause.split(",") if p.strip()]
    items: List[SelectItem] = []

    agg_funcs = ["sum", "avg", "count", "min", "max"]

    for part in parts:
        raw = part
        alias = None

        # Pattern: expr AS alias
        m_as = re.search(r"\s+as\s+([a-zA-Z_][a-zA-Z0-9_]*)$", part, flags=re.IGNORECASE)
        if m_as:
            alias = m_as.group(1).strip()
        else:
            # Fallback: "expr alias"
            m_simple = re.search(r"(.+)\s+([a-zA-Z_][a-zA-Z0-9_]*)$", part)
            if m_simple and "(" not in m_simple.group(2):
                alias = m_simple.group(2).strip()

        is_agg = False
        agg_func = None
        for func in agg_funcs:
            if re.match(rf"\s*{func}\s*\(", part, flags=re.IGNORECASE):
                is_agg = True
                agg_func = func.upper()
                break

        items.append(
            SelectItem(
                raw=raw,
                alias=alias,
                is_aggregate=is_agg,
                agg_func=agg_func,
            )
        )

    return distinct, items


def _parse_from_clause(from_clause: str) -> List[TableRef]:
    """
    Parse the FROM clause including simple JOINs.

    Supports patterns like:
      FROM a
      FROM a t
      FROM a t JOIN b s ON t.id = s.id
      FROM a INNER JOIN b ON ...
    """
    if not from_clause:
        return []

    norm = re.sub(r"\s+", " ", from_clause.strip())
    tokens = norm.split(" ")

    tables: List[TableRef] = []
    i = 0

    # First (main) table
    if i < len(tokens):
        name = tokens[i]
        i += 1
        alias = None
        if i < len(tokens) and tokens[i].lower() not in (
            "join", "inner", "left", "right", "full", "cross", "outer"
        ):
            alias = tokens[i]
            i += 1
        tables.append(TableRef(name=name, alias=alias))

    # Subsequent JOINs
    while i < len(tokens):
        join_type_parts: List[str] = []
        while i < len(tokens) and tokens[i].lower() in (
            "join", "inner", "left", "right", "full", "cross", "outer"
        ):
            join_type_parts.append(tokens[i])
            i += 1

        if not join_type_parts:
            break

        jt = " ".join(join_type_parts).upper()
        if not jt.endswith("JOIN"):
            jt += " JOIN"

        if i >= len(tokens):
            break

        name = tokens[i]
        i += 1
        alias = None
        if i < len(tokens) and tokens[i].lower() != "on":
            alias = tokens[i]
            i += 1

        join_cond = None
        if i < len(tokens) and tokens[i].lower() == "on":
            join_cond = " ".join(tokens[i + 1 :])
            i = len(tokens)

        tables.append(
            TableRef(
                name=name,
                alias=alias,
                join_type=jt,
                join_condition=join_cond,
            )
        )

    return tables


def _parse_group_by_clause(group_clause: Optional[str]) -> List[str]:
    """
    Parse GROUP BY clause into a list of column expressions.
    """
    if not group_clause:
        return []
    return [p.strip() for p in group_clause.split(",") if p.strip()]


def _parse_order_by_clause(order_clause: str) -> List[OrderItem]:
    """
    Parse ORDER BY clause into a list of OrderItem objects.
    """
    items: List[OrderItem] = []
    if not order_clause:
        return items

    parts = [p.strip() for p in order_clause.split(",") if p.strip()]
    for part in parts:
        tokens = part.split()
        if not tokens:
            continue
        direction = "ASC"
        expr = part
        if tokens[-1].lower() in ("asc", "desc"):
            direction = tokens[-1].upper()
            expr = " ".join(tokens[:-1])
        items.append(OrderItem(expr=expr.strip(), direction=direction))

    return items


def _parse_limit_clause(limit_clause: str) -> (Optional[int], Optional[int]):
    """
    Parse LIMIT/OFFSET patterns.

    Supports:
      LIMIT 10
      LIMIT 10 OFFSET 5
      LIMIT 5,10  (offset=5, limit=10)
    """
    if not limit_clause:
        return None, None

    txt = limit_clause.strip()

    # "10 offset 5"
    m = re.match(r"(\d+)\s+offset\s+(\d+)", txt, flags=re.IGNORECASE)
    if m:
        limit = int(m.group(1))
        offset = int(m.group(2))
        return limit, offset

    # "5,10"
    m = re.match(r"(\d+)\s*,\s*(\d+)", txt)
    if m:
        offset = int(m.group(1))
        limit = int(m.group(2))
        return limit, offset

    # single number
    m = re.match(r"(\d+)", txt)
    if m:
        return int(m.group(1)), None

    return None, None


def _split_where_clauses(where_clause: str) -> List[str]:
    """
    Very simple WHERE splitter:
    - splits by AND
    - keeps ORs inside the same condition

    This is not a full SQL parser, but works for many analytic queries.
    """
    if not where_clause:
        return []
    parts = re.split(r"\s+and\s+", where_clause, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


# ---------- Main parse entry point ---------- #


def parse_sql(query: str) -> SqlQuery:
    """
    Parse a SQL SELECT-style query into a SqlQuery structure
    using simple string-based heuristics.

    This is not a full SQL grammar, but it is sufficient for
    many analytic-style queries (SELECT-FROM-WHERE-GROUP-HAVING-ORDER-LIMIT).
    """
    q = query.strip().rstrip(";")

    select_clause = _split_clause(q, "select", ["from"])
    from_clause   = _split_clause(q, "from",   ["where", "group by", "having", "order by", "limit"])
    where_clause  = _split_clause(q, "where",  ["group by", "having", "order by", "limit"])
    group_clause  = _split_clause(q, "group by", ["having", "order by", "limit"])
    having_clause = _split_clause(q, "having", ["order by", "limit"])
    order_clause  = _split_clause(q, "order by", ["limit"])
    limit_clause  = _split_clause(q, "limit", [])

    distinct, select_items = _parse_select_clause(select_clause or "")
    tables = _parse_from_clause(from_clause or "")
    group_by = _parse_group_by_clause(group_clause)
    order_items = _parse_order_by_clause(order_clause or "")
    limit, offset = _parse_limit_clause(limit_clause or "")
    where_clauses = _split_where_clauses(where_clause or "")

    return SqlQuery(
        raw=query,
        distinct=distinct,
        select_items=select_items,
        tables=tables,
        where=where_clause,
        where_clauses=where_clauses,
        group_by=group_by,
        having=having_clause,
        order_by_items=order_items,
        limit=limit,
        offset=offset,
    )


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

    q = parse_sql(test_query)
    print("DISTINCT:", q.distinct)
    print("SELECT:")
    for s in q.select_items:
        print(" ", s)
    print("TABLES:")
    for t in q.tables:
        print(" ", t)
    print("WHERE:", q.where)
    print("WHERE clauses:", q.where_clauses)
    print("GROUP BY:", q.group_by)
    print("HAVING:", q.having)
    print("ORDER BY:", [(o.expr, o.direction) for o in q.order_by_items])
    print("LIMIT:", q.limit, "OFFSET:", q.offset)
