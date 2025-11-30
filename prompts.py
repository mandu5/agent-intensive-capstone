"""Prompt templates for Smart Study Buddy agents."""

from __future__ import annotations

from typing import List, Optional


def format_agent_prompt(
    agent_name: str,
    instructions: str,
    context: str,
    memory: Optional[List[str]] = None,
) -> str:
    """
    Format a prompt for an agent with memory and context.

    Args:
        agent_name: Name of the agent (e.g., "Researcher", "QuizMaster")
        instructions: Role-specific instructions for the agent
        context: Current context/input for the agent
        memory: Optional list of memory entries from previous interactions

    Returns:
        Formatted prompt string
    """
    memory_section = "\n".join(memory) if memory else "None yet."

    return f"""You are the {agent_name} agent.
Instructions: {instructions}

Session memory (may be empty):
{memory_section}
---
Focused input:
{context}
"""


def format_researcher_prompt(topic: str, search_digest: str) -> str:
    """
    Format prompt for the Researcher agent.

    Args:
        topic: Topic to research
        search_digest: Search results digest

    Returns:
        Formatted prompt string
    """
    return f"""Topic: {topic}
Use the search digest as factual grounding. Provide:
- A brief overview
- 3-5 bullet points of core insights
- One memorable example or analogy

Search digest:
{search_digest}
"""


def format_quiz_master_prompt(study_note: str) -> str:
    """
    Format prompt for the Quiz Master agent.

    Args:
        study_note: Study note to generate quiz from

    Returns:
        Formatted prompt string
    """
    return f"""You must return valid JSON only.
Study note source:
{study_note}
"""


def format_tutor_prompt(
    question: str,
    options: List[str],
    correct_answer: str,
    user_answer: Optional[str],
    study_note: str,
) -> str:
    """
    Format prompt for the Tutor agent.

    Args:
        question: Quiz question
        options: Available answer options
        correct_answer: Correct answer
        user_answer: User's answer (or None)
        study_note: Study note for reference

    Returns:
        Formatted prompt string
    """
    return f"""Question: {question}
Options: {options}
Correct Answer: {correct_answer}
Learner Answer: {user_answer or 'No answer provided'}
Study Note:
{study_note}
"""

