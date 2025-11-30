# Smart Study Buddy – Kaggle Submission Template

Use this template as a starting point for the required Kaggle writeup. Replace the placeholder text with details from your own build, experiment logs, and demo screenshots.

---

## Title
Smart Study Buddy: AI Tutor for Fast Active Recall

## Subtitle
Concierge Agent that researches, quizzes, and coaches in under a minute.

## Track
Concierge Agents

## Problem (Why)
Learners waste time collecting trustworthy study material and often fall into passive reading, which hurts retention. The last 24–48 hours before an exam are especially critical, yet most students spend it searching, summarizing, and manually crafting practice problems.

## Solution (What)
Smart Study Buddy automates the revision loop by chaining three Gemini-powered agents:
1. **Researcher** – uses a web-search tool to gather the latest facts and distill them into a concise study note.
2. **Quiz Master** – turns the note into JSON-formatted multiple-choice questions for active recall.
3. **Tutor** – grades the learner, explains the reasoning, and stores takeaways for future sessions.

## Value (Impact)
- Cuts prep time by ~90% for new topics (from ~30 minutes of manual prep to <3 minutes).
- Reinforces memory with immediate feedback and context-aware coaching.
- Produces reusable study notes plus quiz logs that can be revisited anytime.

## Architecture Overview
```
User Prompt -> Researcher (Gemini + DuckDuckGo Tool)
              -> Quiz Master (Gemini, structured JSON output)
              -> Tutor (Gemini + session memory)
```
- Session memory keeps the last 10 artifacts (study notes, quizzes, feedback) to ground later agents.
- Observability: console logging shows tool usage, agent calls, and failures for quick debugging.

## Key Implementation Highlights
- **Multi-agent (Sequential)**: Researcher → Quiz Master → Tutor pipeline with isolated instructions and role-specific prompts.
- **Tool Use**: Custom DuckDuckGo search wrapper (`SearchTool`) with exponential backoff retry logic for network resilience.
- **Sessions & Memory**: Configurable memory buffer (default: 10 artifacts) appended after each agent call to maintain context across the session.
- **Structured Generation**: Quiz Master outputs strict JSON with robust parsing (handles markdown code blocks, validates fields, ensures correct_answer is in options).
- **Configuration Management**: Centralized `AppConfig` class with environment variable support and validation.
- **Error Handling**: Comprehensive error handling with specific exception types, retry logic, and user-friendly error messages.
- **Testing**: Full test suite with 29 tests covering all core functionality using pytest and mocks.
- **CLI UX**: `python smart_study_buddy.py --topic "Photosynthesis" --questions 2` for reproducible demos with input validation and retry logic.

## Setup & Repro Steps
1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API key**:
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   # Or export: export GEMINI_API_KEY="your-key"
   # Get your key from: https://aistudio.google.com/app/apikey
   ```

3. **Run the agent**:
   ```bash
   python smart_study_buddy.py --topic "Photosynthesis" --questions 2
   ```

4. **Run tests** (optional):
   ```bash
   pytest tests/ -v
   ```

5. **Record a screen capture** (≤3 minutes) showing the full loop for the video bonus.

## Metrics / Evaluation
- **Test Coverage**: 29 unit tests covering configuration, prompts, search tool, quiz parsing, and core functionality (all passing).
- **Manual Testing**: Validated across multiple topics including biology (Photosynthesis), demonstrating end-to-end workflow.
- **Performance**: 
  - Search execution: ~0.3 seconds per query
  - Study note generation: ~3-5 seconds
  - Quiz generation: ~2-4 seconds
  - Total latency per question: ~8-12 seconds with `gemini-1.5-flash`
- **Reliability**: 
  - Robust error handling with exponential backoff retry logic for network failures
  - JSON parsing with regex-based markdown code block extraction
  - Input validation with retry mechanism for user answers

## Bonus Evidence (Optional but Recommended)
- **Gemini Usage**: ✅ All agents run on Gemini 1.5 Flash (configurable via `GEMINI_MODEL` environment variable, default: `gemini-1.5-flash`). Mentioned in README and ready for video demonstration.
- **Code Quality**: ✅ Comprehensive test suite (29 tests), clean code architecture with separation of concerns (config, prompts, core logic), and robust error handling.
- **Deployment**: Ready for Cloud Run / Agent Engine deployment. The modular architecture makes it easy to wrap in a web API or deploy as a service.
- **Video**: Include a YouTube link demonstrating the workflow (problem → agent flow → live demo).

## Future Work
- Add spaced-repetition scheduling with persistent storage.
- Plug in RAG for proprietary documents.
- Expand to multimodal study aids (e.g., diagrams, code walkthroughs).

---
Fill in quantitative claims, screenshots, and any additional experimentation details before submitting to Kaggle.
