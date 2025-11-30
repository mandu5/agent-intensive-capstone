"""Smart Study Buddy CLI.

This script demonstrates a multi-agent study assistant that:
- Uses a web-search tool (DuckDuckGo) to gather up-to-date references.
- Chains three specialized Gemini-powered agents (Researcher, QuizMaster, Tutor).
- Maintains a lightweight in-memory session log to ground future prompts.

Run locally:
    pip install -r requirements.txt
    export GEMINI_API_KEY="your-key"
    python smart_study_buddy.py --topic "Photosynthesis" --questions 2
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import List, Optional

from duckduckgo_search import DDGS
import google.generativeai as genai

from config import AppConfig
from prompts import (
    format_agent_prompt,
    format_quiz_master_prompt,
    format_researcher_prompt,
    format_tutor_prompt,
)

# ----------------------------------------------------------------------------
# Configuration & logging
# ----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
LOGGER = logging.getLogger("smart-study-buddy")

# Configuration will be loaded in main() to avoid import-time errors in tests


# ----------------------------------------------------------------------------
# Tooling layer
# ----------------------------------------------------------------------------
@dataclass
class SearchTool:
    """Simple wrapper around DuckDuckGo Search to serve as an agent tool."""

    max_results: int
    max_retries: int
    retry_delay: float

    def run(self, query: str) -> str:
        """
        Execute a web search with retry logic.

        Args:
            query: Search query string

        Returns:
            Formatted search results or error message
        """
        if not query:
            return "No query provided."

        LOGGER.info("[Tool] Searching web for '%s' (top %d results)", query, self.max_results)

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                snippets: List[str] = []
                with DDGS() as ddgs:
                    for row in ddgs.text(query, max_results=self.max_results):
                        body = row.get("body") or ""
                        title = row.get("title") or "Untitled"
                        snippets.append(f"- {title}: {body}")

                if snippets:
                    return "\n".join(snippets)
                return "No public snippets were found."

            except (ConnectionError, TimeoutError) as err:
                last_error = err
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    LOGGER.warning(
                        "Search attempt %d/%d failed: %s. Retrying in %.1f seconds...",
                        attempt,
                        self.max_retries,
                        err,
                        wait_time,
                    )
                    time.sleep(wait_time)
                else:
                    LOGGER.error("All search attempts failed after %d retries", self.max_retries)

            except Exception as err:  # pragma: no cover - network variances
                LOGGER.warning("DuckDuckGo search failed with unexpected error: %s", err)
                return f"Search failed: {err}"

        # If we get here, all retries failed
        error_msg = f"Search failed after {self.max_retries} attempts"
        if last_error:
            error_msg += f": {last_error}"
        return error_msg


# ----------------------------------------------------------------------------
# Base agent abstraction
# ----------------------------------------------------------------------------
@dataclass
class Agent:
    """Wrapper around a GenerativeModel with role-specific instructions."""

    name: str
    instructions: str
    model_name: str
    response_mime_type: str = "text/plain"

    def __post_init__(self) -> None:
        self._model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={"response_mime_type": self.response_mime_type},
        )

    def run(self, context: str, memory: Optional[List[str]] = None) -> str:
        """
        Execute the agent with given context and memory.

        Args:
            context: Current context/input for the agent
            memory: Optional list of memory entries from previous interactions

        Returns:
            Agent response text

        Raises:
            Exception: If the agent call fails
        """
        compiled_prompt = format_agent_prompt(
            agent_name=self.name,
            instructions=self.instructions,
            context=context,
            memory=memory,
        )

        try:
            response = self._model.generate_content(compiled_prompt)
        except Exception as exc:  # pragma: no cover - SDK surface
            LOGGER.error("%s agent call failed: %s", self.name, exc)
            raise

        return (response.text or "").strip()


# ----------------------------------------------------------------------------
# Pipeline logic
# ----------------------------------------------------------------------------
@dataclass
class QuizItem:
    question: str
    options: List[str]
    correct_answer: str
    explanation: Optional[str] = None


class SmartStudyBuddy:
    """Coordinates the tool + agents to deliver a study session."""

    def __init__(
        self,
        config: AppConfig,
        search_tool: Optional[SearchTool] = None,
    ) -> None:
        """
        Initialize Smart Study Buddy with configuration.

        Args:
            config: Application configuration
            search_tool: Optional search tool instance (uses config defaults if not provided)
        """
        self.config = config
        self.memory: List[str] = []
        self.search_tool = search_tool or SearchTool(
            max_results=config.default_max_results,
            max_retries=config.search_max_retries,
            retry_delay=config.search_retry_delay,
        )

        self.researcher = Agent(
            name="Researcher",
            instructions=(
                "Aggregate the most important definitions, core principles,"
                " and real-world examples. Cite search snippets concisely."
            ),
            model_name=config.gemini_model,
        )
        self.quiz_master = Agent(
            name="QuizMaster",
            instructions=(
                "Create a single multiple-choice question based on the study note."
                " Respond with strict JSON containing keys question, options (list),"
                " correct_answer, explanation."
            ),
            model_name=config.gemini_model,
            response_mime_type="application/json",
        )
        self.tutor = Agent(
            name="Tutor",
            instructions=(
                "Evaluate the learner's answer, explain correctness, and add a follow-up tip."
                " Encourage active recall and reference the study note when helpful."
            ),
            model_name=config.gemini_model,
        )

    # --------------------------- public API ---------------------------
    def interactive_session(self, topic: str, questions: int = 1) -> None:
        """
        Run an end-to-end study session via the terminal.

        Args:
            topic: Topic to study
            questions: Number of quiz questions to generate
        """
        study_note = self._generate_study_note(topic)
        LOGGER.info("Study note ready. Generating %d quiz question(s)...", questions)

        correct = 0
        for idx in range(1, questions + 1):
            quiz = self._generate_quiz(study_note)
            if not quiz:
                LOGGER.error("Quiz generation failed. Aborting session.")
                return

            print(f"\n==== Quiz {idx} / {questions} ====")
            print(quiz.question)
            for option_idx, option in enumerate(quiz.options, start=1):
                print(f"  {option_idx}. {option}")

            user_answer = self._get_user_answer(quiz.options)
            if user_answer is None:  # User quit
                break

            normalized = self._normalize_answer(user_answer, quiz.options)
            feedback = self._grade_and_feedback(quiz, normalized, study_note)
            print("\nFeedback:\n" + feedback)

            if normalized and normalized.lower() == quiz.correct_answer.lower():
                correct += 1

        if questions:
            print(
                f"\nSession complete. Score: {correct}/{questions}"
                f" ({(correct/questions)*100:.0f}% accuracy)."
            )

    # -------------------------- internals ----------------------------
    def _remember(self, entry: str) -> None:
        """
        Add an entry to memory, maintaining the configured limit.

        Args:
            entry: Memory entry to add
        """
        self.memory.append(entry)
        # Keep memory bounded to avoid prompt bloat
        if len(self.memory) > self.config.memory_limit:
            self.memory = self.memory[-self.config.memory_limit :]

    def _generate_study_note(self, topic: str) -> str:
        """
        Generate a study note for the given topic.

        Args:
            topic: Topic to research

        Returns:
            Generated study note
        """
        search_digest = self.search_tool.run(topic)
        context = format_researcher_prompt(topic=topic, search_digest=search_digest)

        note = self.researcher.run(context, self.memory)
        self._remember(f"StudyNote::{note}")
        return note

    def _generate_quiz(self, study_note: str) -> Optional[QuizItem]:
        """
        Generate a quiz question from a study note.

        Args:
            study_note: Study note to generate quiz from

        Returns:
            QuizItem if successful, None otherwise
        """
        context = format_quiz_master_prompt(study_note=study_note)

        raw_response = self.quiz_master.run(context, self.memory)
        quiz = self._parse_quiz(raw_response)
        if quiz:
            self._remember(f"Quiz::{quiz.question}")
        return quiz

    def _grade_and_feedback(
        self, quiz: QuizItem, user_answer: Optional[str], study_note: str
    ) -> str:
        """
        Grade user answer and generate feedback.

        Args:
            quiz: Quiz item with question and correct answer
            user_answer: User's answer
            study_note: Study note for reference

        Returns:
            Feedback string
        """
        context = format_tutor_prompt(
            question=quiz.question,
            options=quiz.options,
            correct_answer=quiz.correct_answer,
            user_answer=user_answer,
            study_note=study_note,
        )

        feedback = self.tutor.run(context, self.memory)
        self._remember(f"Feedback::{feedback}")
        return feedback

    def _get_user_answer(self, options: List[str]) -> Optional[str]:
        """
        Get and validate user answer with retry logic.

        Args:
            options: List of available answer options

        Returns:
            User's answer string, or None if user quits
        """
        for attempt in range(1, self.config.max_input_retries + 1):
            user_input = input(
                f"Your answer (number or text, 'q' to quit) [{attempt}/{self.config.max_input_retries}]: "
            ).strip()

            if not user_input:
                if attempt < self.config.max_input_retries:
                    print("Please provide an answer or 'q' to quit.")
                    continue
                else:
                    print("No answer provided. Moving to next question.")
                    return None

            if user_input.lower() == "q":
                return None

            # Validate numeric input
            if user_input.isdigit():
                idx = int(user_input) - 1
                if 0 <= idx < len(options):
                    return user_input
                else:
                    if attempt < self.config.max_input_retries:
                        print(f"Please enter a number between 1 and {len(options)}.")
                        continue
                    else:
                        print(f"Invalid number. Using '{user_input}' as text answer.")
                        return user_input

            # Text input is always accepted
            return user_input

        return None

    @staticmethod
    def _normalize_answer(user_input: str, options: List[str]) -> Optional[str]:
        """
        Normalize user input to match an option.

        Args:
            user_input: Raw user input
            options: List of available options

        Returns:
            Normalized answer matching an option, or original input
        """
        if not user_input:
            return None

        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(options):
                return options[idx]

        user_input_lower = user_input.lower()
        for option in options:
            if option.lower().startswith(user_input_lower):
                return option
        return user_input  # fallback to raw text

    @staticmethod
    def _parse_quiz(payload: str) -> Optional[QuizItem]:
        """
        Parse quiz JSON from agent response with robust error handling.

        Args:
            payload: Raw response from quiz master agent

        Returns:
            QuizItem if parsing succeeds, None otherwise
        """
        if not payload:
            return None

        # Step 1: Extract JSON from markdown code blocks using regex
        cleaned = payload.strip()

        # Match JSON in markdown code blocks (```json ... ``` or ``` ... ```)
        code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        matches = re.findall(code_block_pattern, cleaned, re.DOTALL | re.IGNORECASE)
        if matches:
            # Use the last match (most likely the actual JSON)
            cleaned = matches[-1].strip()
        else:
            # If no code blocks, try to find JSON object boundaries
            json_pattern = r"\{.*\}"
            json_match = re.search(json_pattern, cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(0).strip()

        # Step 2: Parse JSON
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            LOGGER.error("Quiz JSON parsing failed: %s\nPayload was:\n%s", exc, payload)
            return None

        # Step 3: Validate and extract fields
        question = data.get("question")
        options = data.get("options", [])
        answer = data.get("correct_answer")
        explanation = data.get("explanation")

        # Validate required fields
        if not question or not isinstance(question, str):
            LOGGER.error("Quiz JSON missing or invalid 'question' field: %s", data)
            return None

        if not options or not isinstance(options, list):
            LOGGER.error("Quiz JSON missing or invalid 'options' field: %s", data)
            return None

        if len(options) < 2:
            LOGGER.error("Quiz JSON 'options' must have at least 2 items: %s", data)
            return None

        if not answer or not isinstance(answer, str):
            LOGGER.error("Quiz JSON missing or invalid 'correct_answer' field: %s", data)
            return None

        # Validate that correct_answer is in options
        if answer not in options:
            LOGGER.warning(
                "Correct answer '%s' not found in options. Using first option as fallback.",
                answer,
            )
            answer = options[0]

        return QuizItem(
            question=question,
            options=options,
            correct_answer=answer,
            explanation=explanation,
        )


# ----------------------------------------------------------------------------
# CLI entrypoint
# ----------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Smart Study Buddy agent.")
    parser.add_argument("--topic", "-t", help="Topic to study. If omitted you'll be prompted.")
    parser.add_argument("--questions", "-q", type=int, default=1, help="Number of quiz questions to generate.")
    parser.add_argument(
        "--max-results",
        type=int,
        default=3,
        help="How many search results to fetch for grounding context.",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the CLI."""
    # Load configuration (only when actually running, not during import)
    try:
        config = AppConfig.from_env()
    except EnvironmentError as e:
        LOGGER.error(str(e))
        raise

    # Configure Gemini API
    genai.configure(api_key=config.gemini_api_key)

    args = parse_args()
    topic = args.topic or input("Enter a topic to study: ").strip()
    if not topic:
        raise ValueError("A topic is required to run the study buddy.")

    # Override config with CLI arguments if provided
    if args.max_results:
        config.default_max_results = args.max_results

    search_tool = SearchTool(
        max_results=config.default_max_results,
        max_retries=config.search_max_retries,
        retry_delay=config.search_retry_delay,
    )

    buddy = SmartStudyBuddy(config=config, search_tool=search_tool)
    buddy.interactive_session(topic=topic, questions=max(1, args.questions))


if __name__ == "__main__":
    main()
