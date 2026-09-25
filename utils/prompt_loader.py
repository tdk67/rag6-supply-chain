"""Prompt template loader for LLM reasoning and guardrails.

Enforces clean separation between application logic and prompt definitions.
"""

from pathlib import Path
from typing import Any, Dict, Optional
from utils.config import resolve_path, load_config


class PromptLoader:
    """Manages loading and parameter substitution for prompt template files."""

    def __init__(self, prompts_dir: Optional[str | Path] = None):
        if prompts_dir is not None:
            self.prompts_dir = resolve_path(prompts_dir)
        else:
            cfg = load_config()
            rel_path = cfg.get("paths", {}).get("prompts_dir", "prompts")
            self.prompts_dir = resolve_path(rel_path)

    def load(self, prompt_filename: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """Load a prompt file from the prompts directory and render parameterized placeholders.

        Args:
            prompt_filename: Name of the prompt file (e.g., 'system_prompt.txt').
            variables: Optional dictionary of variables for substitution.

        Returns:
            Rendered prompt string.
        """
        prompt_path = self.prompts_dir / prompt_filename
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt template '{prompt_filename}' not found at {prompt_path}")

        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        if variables:
            # Use safe format replacement
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                if placeholder in template:
                    template = template.replace(placeholder, str(value))

        return template


# Singleton instance for quick access
_default_loader: Optional[PromptLoader] = None


def get_prompt(prompt_filename: str, variables: Optional[Dict[str, Any]] = None) -> str:
    """Convenience function to load a prompt using the default PromptLoader."""
    global _default_loader
    if _default_loader is None:
        _default_loader = PromptLoader()
    return _default_loader.load(prompt_filename, variables)
