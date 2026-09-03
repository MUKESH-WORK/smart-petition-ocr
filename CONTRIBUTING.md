# Contributing to GDP Assistant

Thank you for your interest in contributing to **GDP Assistant (District Revenue Officer Grievance Day Petition AI Platform)**. We welcome contributions from developers, researchers, civil servants, and civic-tech enthusiasts worldwide.

This project follows engineering standards modeled after modern open-source foundations and Google Engineering Practices.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Guiding Architectural Principles](#guiding-architectural-principles)
3. [Development Workflow](#development-workflow)
   - [Fork & Clone](#fork--clone)
   - [Branching Conventions](#branching-conventions)
   - [Commit Message Specification](#commit-message-specification)
4. [Setting Up Your Local Environment](#setting-up-your-local-environment)
   - [Backend (FastAPI, Python 3.11+, PostgreSQL 16)](#backend-setup)
   - [Frontend (React 19, Vite, Vanilla CSS)](#frontend-setup)
5. [Coding & Style Standards](#coding--style-standards)
   - [Python Backend Guidelines](#python-backend-guidelines)
   - [Frontend JavaScript / React Guidelines](#frontend-javascript--react-guidelines)
6. [Testing & Quality Assurance](#testing--quality-assurance)
7. [Submitting Pull Requests](#submitting-pull-requests)
8. [License](#license)

---

## Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for everyone, regardless of background, gender, identity, experience level, or nationality. 

* Treat all contributors and users with respect and empathy.
* Focus on constructive feedback and objective code review.
* Keep communications professional and aligned with public interest civic technology.

---

## Guiding Architectural Principles

Before writing code, please review the core architectural tenets governing GDP Assistant:

1. **The Postgres-First Law**:
   * One database. Single source of truth.
   * **Do not** introduce Redis, RabbitMQ, Kafka, Pinecone, or MongoDB.
   * PostgreSQL 16 satisfies all workloads:
     * Vector Search via `pgvector` (HNSW).
     * Full-Text Search via `tsvector` + `GIN` indexes.
     * Document storage via `JSONB`.
     * Task queuing via `FOR UPDATE SKIP LOCKED` tables.
     * Document binary storage via `BYTEA` + local disk caching.
2. **Anti-Hallucination Barrier**:
   * All AI-generated outputs (summaries, action items, routing suggestions) must be strictly grounded against OCR source text with verifiable page citations.
   * Heuristic entity extraction and regex validation must run as verification guards.
3. **Data Privacy & Aadhaar Compliance**:
   * PII such as Aadhaar numbers must be automatically masked (`XXXX-XXXX-1234`) prior to database persistence.
   * Phone numbers, survey numbers, and petitioner names must be cross-validated against master revenue tables.
4. **Offline & Edge Capability**:
   * The platform must run on consumer-grade CPU hardware (8GB-16GB RAM) without requiring paid proprietary cloud AI APIs.

---

## Development Workflow

### Fork & Clone

1. Fork the repository on GitHub:
   ```bash
   git clone https://github.com/<your-username>/GDP_Assistant.git
   cd GDP_Assistant
   ```
2. Set up the upstream remote:
   ```bash
   git remote add upstream https://github.com/original-org/GDP_Assistant.git
   ```

### Branching Conventions

Name branches descriptively using standard prefixes:

* `feat/<feature-name>`: New capabilities or functional enhancements.
* `fix/<bug-description>`: Bug fixes and stability patches.
* `perf/<optimization>`: Performance optimizations (e.g., OCR latency, query indexing).
* `refactor/<scope>`: Code refactoring without behavioral alterations.
* `docs/<topic>`: Documentation updates or guides.
* `test/<scope>`: Adding or enhancing unit and integration test suites.

Example:
```bash
git checkout -b feat/tamil-phonetic-search
```

### Commit Message Specification

We strictly follow the **Conventional Commits** specification:

```text
<type>(<scope>): <short summary>

[optional body explaining motivation and architectural tradeoffs]

[optional footer(s) such as issue references]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.

**Examples**:
* `feat(ocr): add adaptive binarization preprocessing for low-contrast scans`
* `fix(analyzer): add timeout handling to prevent worker thread hang on CPU inference`
* `docs(readme): add bilingual prompt architecture diagram`

---

## Setting Up Your Local Environment

### Backend Setup

1. **Prerequisites**:
   * Python 3.11 or higher
   * PostgreSQL 16 with `pgvector` extension (or Docker)
   * Local Ollama server (running `qwen2.5:3b` or `qwen2.5:1.5b`)

2. **Initialize Python Environment**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Start PostgreSQL with pgvector**:
   ```bash
   docker compose up -d
   ```

4. **Run Migrations & Seed Locations**:
   ```bash
   alembic upgrade head
   python init_db.py
   ```

5. **Start the API Server**:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

### Frontend Setup

1. **Prerequisites**:
   * Node.js v18.0.0 or higher
   * npm v9.0.0 or higher

2. **Install Dependencies & Start**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Access the dashboard at `http://localhost:5174/`.

---

## Coding & Style Standards

### Python Backend Guidelines

* **Code Formatting**: Format code using `black` (line length 100) and sort imports with `isort`.
* **Static Typing**: Use Python type hints throughout (`typing.Optional`, `typing.List`, `typing.Dict`, Pydantic models).
* **Asynchronous I/O**: Use `async`/`await` for all database interactions and HTTP network calls. Never use blocking synchronous operations in FastAPI routes.
* **SQLAlchemy 2.0**: Use `select()`, `update()`, and parameterized `text()` queries to eliminate SQL injection vulnerabilities.

### Frontend JavaScript / React Guidelines

* **Component Design**: Build modular, single-responsibility functional components with standard React hooks (`useState`, `useEffect`, `useCallback`, `useMemo`).
* **Styling**: Maintain vanilla CSS design system tokens. Avoid introducing heavy utility libraries unless explicitly requested.
* **Accessibility**: Maintain accessible HTML5 semantic elements, proper ARIA labels, and keyboard navigation support (`Tab`, `Escape`, `Enter`).
* **Resilience**: Always handle asynchronous fetch errors gracefully with user-friendly notices rather than uncaught console exceptions.

---

## Testing & Quality Assurance

All new features and bug fixes must include unit or integration tests:

1. **Backend Tests**:
   ```bash
   cd backend
   pytest tests/ -v
   ```
2. **Frontend Validation**:
   ```bash
   cd frontend
   npm run build
   ```

Ensure all tests pass and static checks report zero errors before opening a pull request.

---

## Submitting Pull Requests

1. **Rebase Before Submitting**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
2. **Push to Your Fork**:
   ```bash
   git push origin <your-branch-name>
   ```
3. **Open a Pull Request**:
   * Provide a clear title and description explaining the problem, the solution, and verification steps.
   * Reference any related issues (e.g., `Closes #42`).
   * Include before-and-after screenshots or log outputs when touching UI or API responses.
4. **Code Review**:
   * Maintainers will review your PR against performance, security, and architectural standards.
   * Address review comments promptly.

---

## License

By contributing to GDP Assistant, you agree that your contributions will be licensed under the **Apache License, Version 2.0**. See the [LICENSE](file:///e:/test_rat/GDP_Assistant/LICENSE) file for details.
