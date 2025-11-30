"""Tests for Smart Study Buddy core functionality."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from config import AppConfig
from smart_study_buddy import QuizItem, SearchTool, SmartStudyBuddy


class TestSearchTool:
    """Test SearchTool class."""

    @patch("smart_study_buddy.DDGS")
    def test_search_success(self, mock_ddgs_class):
        """Test successful search."""
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__.return_value = mock_ddgs
        mock_ddgs.text.return_value = [
            {"title": "Test Title", "body": "Test body"},
            {"title": "Another Title", "body": "Another body"},
        ]
        mock_ddgs_class.return_value = mock_ddgs

        tool = SearchTool(max_results=2, max_retries=1, retry_delay=0.1)
        result = tool.run("test query")

        assert "Test Title" in result
        assert "Test body" in result
        assert "Another Title" in result

    def test_search_empty_query(self):
        """Test search with empty query."""
        tool = SearchTool(max_results=3, max_retries=1, retry_delay=0.1)
        result = tool.run("")
        assert result == "No query provided."

    @patch("smart_study_buddy.DDGS")
    @patch("smart_study_buddy.time.sleep")
    def test_search_retry_on_connection_error(self, mock_sleep, mock_ddgs_class):
        """Test search retry logic on connection error."""
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__.return_value = mock_ddgs
        mock_ddgs.text.side_effect = [
            ConnectionError("Connection failed"),
            [{"title": "Success", "body": "Success body"}],
        ]
        mock_ddgs_class.return_value = mock_ddgs

        tool = SearchTool(max_results=3, max_retries=2, retry_delay=0.1)
        result = tool.run("test query")

        assert "Success" in result
        assert mock_sleep.called  # Verify retry delay was called

    @patch("smart_study_buddy.DDGS")
    def test_search_no_results(self, mock_ddgs_class):
        """Test search with no results."""
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__.return_value = mock_ddgs
        mock_ddgs.text.return_value = []
        mock_ddgs_class.return_value = mock_ddgs

        tool = SearchTool(max_results=3, max_retries=1, retry_delay=0.1)
        result = tool.run("test query")

        assert "No public snippets were found." in result


class TestQuizParsing:
    """Test quiz parsing functionality."""

    def test_parse_quiz_valid_json(self):
        """Test parsing valid JSON quiz."""
        payload = json.dumps({
            "question": "What is 2+2?",
            "options": ["3", "4", "5", "6"],
            "correct_answer": "4",
            "explanation": "Basic math",
        })
        quiz = SmartStudyBuddy._parse_quiz(payload)
        assert quiz is not None
        assert quiz.question == "What is 2+2?"
        assert quiz.options == ["3", "4", "5", "6"]
        assert quiz.correct_answer == "4"

    def test_parse_quiz_markdown_code_block(self):
        """Test parsing quiz from markdown code block."""
        payload = """Here's the quiz:
```json
{
  "question": "What is X?",
  "options": ["A", "B"],
  "correct_answer": "A"
}
```
Some extra text."""
        quiz = SmartStudyBuddy._parse_quiz(payload)
        assert quiz is not None
        assert quiz.question == "What is X?"

    def test_parse_quiz_missing_fields(self):
        """Test parsing quiz with missing required fields."""
        payload = json.dumps({"question": "Test?"})
        quiz = SmartStudyBuddy._parse_quiz(payload)
        assert quiz is None

    def test_parse_quiz_invalid_options(self):
        """Test parsing quiz with invalid options."""
        payload = json.dumps({
            "question": "Test?",
            "options": ["Only one"],
            "correct_answer": "Only one",
        })
        quiz = SmartStudyBuddy._parse_quiz(payload)
        assert quiz is None

    def test_parse_quiz_answer_not_in_options(self):
        """Test parsing quiz where answer is not in options."""
        payload = json.dumps({
            "question": "Test?",
            "options": ["A", "B"],
            "correct_answer": "C",
        })
        quiz = SmartStudyBuddy._parse_quiz(payload)
        # Should fallback to first option
        assert quiz is not None
        assert quiz.correct_answer == "A"

    def test_parse_quiz_empty_payload(self):
        """Test parsing empty payload."""
        quiz = SmartStudyBuddy._parse_quiz("")
        assert quiz is None

    def test_parse_quiz_invalid_json(self):
        """Test parsing invalid JSON."""
        payload = "This is not JSON {"
        quiz = SmartStudyBuddy._parse_quiz(payload)
        assert quiz is None


class TestAnswerNormalization:
    """Test answer normalization."""

    def test_normalize_numeric_answer(self):
        """Test normalizing numeric answer."""
        options = ["Apple", "Banana", "Cherry"]
        result = SmartStudyBuddy._normalize_answer("2", options)
        assert result == "Banana"

    def test_normalize_text_answer_exact_match(self):
        """Test normalizing text answer with exact match."""
        options = ["Apple", "Banana", "Cherry"]
        result = SmartStudyBuddy._normalize_answer("Banana", options)
        assert result == "Banana"

    def test_normalize_text_answer_prefix_match(self):
        """Test normalizing text answer with prefix match."""
        options = ["Apple", "Banana", "Cherry"]
        result = SmartStudyBuddy._normalize_answer("ban", options)
        assert result == "Banana"

    def test_normalize_empty_answer(self):
        """Test normalizing empty answer."""
        options = ["Apple", "Banana"]
        result = SmartStudyBuddy._normalize_answer("", options)
        assert result is None

    def test_normalize_invalid_number(self):
        """Test normalizing invalid number."""
        options = ["Apple", "Banana"]
        result = SmartStudyBuddy._normalize_answer("99", options)
        assert result == "99"  # Falls back to raw text


class TestSmartStudyBuddy:
    """Test SmartStudyBuddy class."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return AppConfig(gemini_api_key="test-key")

    @pytest.fixture
    def mock_search_tool(self):
        """Create a mock search tool."""
        tool = Mock(spec=SearchTool)
        tool.run.return_value = "Test search results"
        return tool

    def test_remember_within_limit(self, config, mock_search_tool):
        """Test memory management within limit."""
        buddy = SmartStudyBuddy(config=config, search_tool=mock_search_tool)
        for i in range(5):
            buddy._remember(f"Entry {i}")
        assert len(buddy.memory) == 5

    def test_remember_exceeds_limit(self, config, mock_search_tool):
        """Test memory management when exceeding limit."""
        buddy = SmartStudyBuddy(config=config, search_tool=mock_search_tool)
        config.memory_limit = 3
        for i in range(5):
            buddy._remember(f"Entry {i}")
        assert len(buddy.memory) == 3
        assert buddy.memory[0] == "Entry 2"  # First two should be removed

    @patch("smart_study_buddy.Agent")
    def test_generate_study_note(self, mock_agent_class, config, mock_search_tool):
        """Test study note generation."""
        mock_agent = Mock()
        mock_agent.run.return_value = "Generated study note"
        mock_agent_class.return_value = mock_agent

        buddy = SmartStudyBuddy(config=config, search_tool=mock_search_tool)
        buddy.researcher = mock_agent

        note = buddy._generate_study_note("Test Topic")
        assert note == "Generated study note"
        assert len(buddy.memory) == 1
        assert "StudyNote::" in buddy.memory[0]

