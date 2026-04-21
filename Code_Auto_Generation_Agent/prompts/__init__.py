"""Prompt template management.

Load and manage system prompts for agents from external files.
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional


class PromptTemplate:
    """Prompt template with variable substitution support.

    Uses {{variable_name}} syntax for placeholders.
    """

    def __init__(self, content: str, name: str = "unknown"):
        self.content = content
        self.name = name

    def render(self, **kwargs: Any) -> str:
        """Render template with variables substituted.

        Args:
            **kwargs: Key-value pairs for variable substitution

        Returns:
            Rendered prompt string
        """
        result = self.content
        for key, value in kwargs.items():
            pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
            result = re.sub(pattern, str(value), result)
        return result

    def list_variables(self) -> list:
        """List all variable placeholders in the template.

        Returns:
            List of variable names
        """
        pattern = r"\{\{\s*(\w+)\s*\}\}"
        return list(set(re.findall(pattern, self.content)))


class PromptLoader:
    """Load prompt templates from files."""

    def __init__(self, prompts_dir: str):
        """Initialize prompt loader.

        Args:
            prompts_dir: Directory containing prompt templates.
        """
        self.prompts_dir = Path(prompts_dir)

    def load(self, name: str) -> PromptTemplate:
        """Load a prompt template by name.

        Args:
            name: Template name (without .md extension)

        Returns:
            PromptTemplate instance

        Raises:
            FileNotFoundError: If template file not found
        """
        filepath = self.prompts_dir / f"{name}.md"

        if not filepath.exists():
            raise FileNotFoundError(
                f"Prompt template '{name}.md' not found in {self.prompts_dir}"
            )

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        return PromptTemplate(content, name)


# Global prompt loader instance
_global_loader: Optional[PromptLoader] = None


def get_prompt_loader(prompts_dir: Optional[str] = None) -> PromptLoader:
    """Get or create the global prompt loader instance.

    Args:
        prompts_dir: Prompt templates directory (required for first init)

    Returns:
        PromptLoader instance
    """
    global _global_loader
    if _global_loader is None or prompts_dir is not None:
        if prompts_dir is None:
            prompts_dir = "./prompts"
        _global_loader = PromptLoader(prompts_dir)
    return _global_loader
