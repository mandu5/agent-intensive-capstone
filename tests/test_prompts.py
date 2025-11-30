"""Tests for prompt templates."""

from prompts import (
    format_agent_prompt,
    format_quiz_master_prompt,
    format_researcher_prompt,
    format_tutor_prompt,
)


class TestPromptTemplates:
    """Test prompt template functions."""

    def test_format_agent_prompt(self):
        """Test agent prompt formatting."""
        prompt = format_agent_prompt(
            agent_name="TestAgent",
            instructions="Do something",
            context="Test context",
            memory=["Memory 1", "Memory 2"],
        )
        assert "TestAgent" in prompt
        assert "Do something" in prompt
        assert "Test context" in prompt
        assert "Memory 1" in prompt
        assert "Memory 2" in prompt

    def test_format_agent_prompt_no_memory(self):
        """Test agent prompt formatting without memory."""
        prompt = format_agent_prompt(
            agent_name="TestAgent",
            instructions="Do something",
            context="Test context",
            memory=None,
        )
        assert "TestAgent" in prompt
        assert "None yet." in prompt

    def test_format_researcher_prompt(self):
        """Test researcher prompt formatting."""
        prompt = format_researcher_prompt(
            topic="Photosynthesis",
            search_digest="Search results here",
        )
        assert "Photosynthesis" in prompt
        assert "Search results here" in prompt

    def test_format_quiz_master_prompt(self):
        """Test quiz master prompt formatting."""
        prompt = format_quiz_master_prompt(study_note="Study note content")
        assert "Study note content" in prompt
        assert "JSON" in prompt

    def test_format_tutor_prompt(self):
        """Test tutor prompt formatting."""
        prompt = format_tutor_prompt(
            question="What is X?",
            options=["A", "B", "C"],
            correct_answer="A",
            user_answer="B",
            study_note="Note content",
        )
        assert "What is X?" in prompt
        assert "A" in prompt
        assert "B" in prompt
        assert "Note content" in prompt

    def test_format_tutor_prompt_no_answer(self):
        """Test tutor prompt formatting without user answer."""
        prompt = format_tutor_prompt(
            question="What is X?",
            options=["A", "B"],
            correct_answer="A",
            user_answer=None,
            study_note="Note",
        )
        assert "No answer provided" in prompt

