# GitHub Repo Tutorial Generator 🤖

An AI-powered agent that automatically explores any public GitHub repository and generates a detailed, code-referenced tutorial using a two-agent architecture.

---

## What It Does

Give it a GitHub repo URL. It navigates the entire codebase, reads the relevant files, and produces a structured 2000+ word tutorial explaining the project — complete with actual code snippets, library explanations, and an end-to-end flow walkthrough.

---

## Architecture

The system uses a **two-agent pipeline** to minimize token usage and cost:

```
User Input (repo URL)
        ↓
┌──────────────────────┐
│   Navigator Agent    │  ← explores repo using 3 tools
│                      │    reads up to 8 core files
│  - get_readme()      │    returns compact JSON summary
│  - return_file_      │
│    structure()       │
│  - Navigate_repo()   │
└──────────┬───────────┘
           │ JSON summary only (~2K tokens)
           ↓
┌──────────────────────┐
│  Tutorial Writer     │  ← no tools, fresh context
│      Agent           │    consumes JSON summary only
│                      │    writes 2000+ word tutorial
└──────────────────────┘
           ↓
     Final Tutorial
```

### Why Two Agents?

A single agent accumulates all file contents in its context across every turn, leading to compounding token costs (e.g. 325K tokens = ~$1/run). By splitting into two separate `Runner.run()` calls, the Navigator's raw file content is discarded after Run 1 — only the compact JSON summary (~2K tokens) crosses the boundary into Run 2.

**Result: ~75K tokens vs ~325K tokens. ~80% cost reduction.**

---

## Tools

### `get_readme(user, repository_name)`
Always called first. Fetches and decodes the README to give the agent context on the project's purpose and architecture before any navigation begins.

### `return_file_structure(user, repository_name)`
Called second. Returns the full recursive file tree of the repository as a formatted string (`path  type`), allowing the agent to plan which files to read before making any Navigate_repo calls.

### `Navigate_repo(url, file_type)`
The core navigation tool. Called repeatedly to either expand a directory (`file_type='tree'`) or read a file's content (`file_type='blob'`). Supports parallel calls for multiple URLs of the same type.

**URL format required:**
```
https://api.github.com/repos/{user}/{repo}/contents/{path}
```

---

## Setup

### Prerequisites
- Python 3.9+
- OpenAI API key
- GitHub Personal Access Token

### Installation

```bash
git clone https://github.com/your-username/gh-repo-tutorial-generator
cd gh-repo-tutorial-generator
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:
```
OPENAI_API_KEY=your_openai_api_key
GITHUB_ACCESS_TOKEN=Bearer your_github_token
```

> **Note:** GitHub's unauthenticated API is rate-limited to 60 requests/hour. A token raises this to 5,000/hour and is required for any real repository.

---

## Usage

```python
import asyncio

tutorial = asyncio.run(generate_tutorial('https://github.com/owner/repo'))
print(tutorial)
```

---

## Cost & Token Management

| Approach | Tokens | Approx Cost (gpt-4o-mini) |
|---|---|---|
| Single agent (no optimizations) | ~325K | ~$1.00 |
| Two-agent pipeline | ~75K | ~$0.20 |

### Built-in guardrails
- Maximum 8 files read per run (prevents runaway navigation)
- Binary and irrelevant files are skipped (`.png`, `.pt`, `LICENSE`, `__pycache__`)
- API errors return gracefully without breaking the navigation loop

---

## Project Structure

```
gh-repo-tutorial-generator/
│
├── tools.py              # get_readme, return_file_structure, Navigate_repo
├── agents.py             # Navigator and Tutorial Writer agent definitions  
├── main.py               # Orchestration — runs both agents sequentially
├── requirements.txt
└── .env.example
```

---

## Requirements

```
openai-agents
openai
requests
pydantic
python-dotenv
```

---

## Limitations

- Only works with **public** GitHub repositories
- Repositories with very deep nesting may require increased file limits
- Code-heavy files (>500 lines) are summarized rather than read in full to stay within context limits
- Default branch assumed to be `master` — repositories using `main` will need a small config change

---

## How It Was Built

This project was built iteratively with a focus on:

- **Tool design as prompts** — docstrings are written as agent contracts (when to call, what to pass, what returns, what next) rather than human documentation
- **Separation of concerns** — navigation logic lives in tools, reasoning lives in the agent, writing lives in a separate agent
- **Cost-aware architecture** — the two-agent split was chosen specifically to prevent context compounding across long navigation loops
