"""
Human interaction compatibility tools.

Some models may try to call a conventional `ask_human` tool when they need
clarification. The product surfaces user questions through normal assistant
messages, so this tool acts as a safe adapter instead of letting an invalid
tool call fail the whole agent run.
"""

import json
import logging

from langchain_core.tools import tool as langchain_tool

logger = logging.getLogger("orchestrator_integration")


def get_human_tools() -> list:
    """Return built-in tools for safe human interaction fallbacks."""

    @langchain_tool
    def ask_human(question: str = "") -> str:
        """
        Ask the user for missing information when the task cannot continue.

        Args:
            question: The exact question that should be shown to the user.

        Returns:
            A JSON payload instructing the assistant to ask the user directly
            in the next response.
        """
        normalized_question = (question or "").strip()
        logger.info("[ask_human] question=%s", normalized_question[:500])
        return json.dumps(
            {
                "requires_user_input": True,
                "question": normalized_question,
                "instruction": (
                    "Ask this question directly in the next assistant message. "
                    "Do not call another tool unless the user provides the missing information."
                ),
            },
            ensure_ascii=False,
        )

    return [ask_human]
