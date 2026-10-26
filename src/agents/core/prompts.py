"""Prompts live in versioned .md files next to each agent, not inside Python code."""

from pathlib import Path


def load_prompt(path: Path, **values: str) -> str:
    return path.read_text(encoding="utf-8").format(**values)
