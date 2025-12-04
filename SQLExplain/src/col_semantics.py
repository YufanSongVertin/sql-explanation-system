# src/col_semantics.py

from functools import lru_cache
from .model import SqlExplainModel, SqlExplainModelConfig


# Reuse a global model instance to avoid reloading the LLM each time
_model = None


def get_model() -> SqlExplainModel:
    """
    Return a global LLM model instance.
    Lazily loads the model on first use.
    """
    global _model
    if _model is None:
        _model = SqlExplainModel(SqlExplainModelConfig())
    return _model


@lru_cache(maxsize=256)
def describe_column_with_llm(table: str, column: str) -> str:
    """
    Use the LLM to produce a short semantic description of a column.
    Cached with LRU to avoid repeated inference for the same (table, column).

    Returns:
        A short, human-readable description of what this column likely means.
    """

    prompt = f"""
    You are acting as a senior data engineer.

    A database table is named "{table}".
    It has a column named "{column}".

    In no more than 12 English words, describe what this column most likely represents.
    Do NOT repeat the column name.
    Do NOT use a colon.
    Do NOT add quotes.
    Output only the short description, nothing else.
    """

    model = get_model()
    text = model.generate_explanation(prompt).strip()

    # Clean up quotes
    text = text.strip('"').strip("'")

    return text
