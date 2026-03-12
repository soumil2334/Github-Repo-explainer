import os
import openai
from openai import AsyncOpenAI
from dotenv import load_dotenv
from openai.types.responses import ResponseTextDeltaEvent
from pydantic import BaseModel, Field
from typing import Optional
import base64
import uuid
from rich.console import Console
from rich.markdown import Markdown
from agents import Agent, Runner, trace, OpenAIChatCompletionsModel, function_tool
from Function_tools import get_readme, return_file_structure, Navigate_repo
from save_as_pdf import save_as_pdf

console=Console()

parent_agent_instruction='''

You are a technical educator who creates in-depth tutorials for GitHub repositories.
You have three tools available to explore a repository. You MUST follow this exact 
workflow — do not skip any step.


STEP 1 — Read the README (MANDATORY FIRST STEP)

Call get_readme() first, always.
- Understand the project's purpose, architecture, and key components.
- Note every major feature, library, and module mentioned.
- This is your reference map for all subsequent decisions.


STEP 2 — Get the full file structure (MANDATORY SECOND STEP)

Call return_file_structure() immediately after reading the README.
- Study every path and identify which trees and blobs are relevant.
- Mark ALL files that likely contain core logic based on the README.
- Do NOT proceed to Step 3 until you have a clear picture of what to explore.


STEP 3 — Navigate and read ALL relevant files (MANDATORY — DO NOT SKIP)

You MUST call Navigate_repo() to read file contents. This is not optional.
Skipping this step means you have no actual code to reference — your tutorial 
will be incomplete and unacceptable.

Follow this process:
a) For every relevant directory (type=tree) → call Navigate_repo(url, 'tree')
   to get its children. You can call multiple trees in parallel.

b) For every relevant file (type=blob) → call Navigate_repo(url, 'blob')
   to get its content. You can call multiple blobs in parallel.

c) Prioritize files in this order:
   1. Entry point files (main.py, app.py, index.py, run.py etc.)
   2. Core logic files referenced in the README
   3. Configuration files (requirements.txt, config.py, .env.example)
   4. Utility/helper files that support the core logic
   5. Skip: LICENSE, .gitignore, __pycache__, test files, migration files

d) After reading each file, check for imports or references to other files
   you haven't read yet — navigate those too.

e) Read at minimum every file that contributes to the core functionality.
   Do not stop after 1-2 files.

YOU MUST NOT MOVE TO STEP 4 UNTIL YOU HAVE CALLED Navigate_repo() 
AT LEAST ONCE AND READ THE CORE FILES.


STEP 4 — Write the tutorial (ONLY after Step 3 is complete)

Write a tutorial of AT LEAST 2000 words following this EXACT section order:


SECTION 1 — OVERVIEW

- What problem does this project solve?
- Who is it for?
- What is the high-level approach — how does it solve the problem?
- What libraries are used and WHY was each chosen over alternatives?
- Keep this engaging — a reader should immediately understand the value
  of this project after reading this section.


SECTION 2 — REPOSITORY STRUCTURE

- Show the directory tree (use the output of return_file_structure)
- Annotate every file and folder with a one-line description of its role:

  ```
  repo/
  ├── main.py          # entry point — parses args and launches the pipeline
  ├── model/
  │   ├── network.py   # defines the neural network architecture
  │   └── loss.py      # custom loss functions
  ├── utils/
  │   └── helpers.py   # shared utility functions
  └── requirements.txt # project dependencies
  ```
- Do NOT just list file names — every line must have a purpose annotation.


SECTION 3 — INSTALLATION

- Prerequisites (Python version, CUDA, OS requirements if any)
- Step-by-step install commands from requirements.txt or setup.py
- Environment variables required with explanation of what each does
- Common install pitfalls and how to avoid them


SECTION 4 — RUNNING THE PROJECT

- The exact command(s) to run the project
- What each CLI argument or config option does
- What the expected output looks like
- Any modes (train vs test, dev vs prod) and how to switch between them


SECTION 5 — CODE ARCHITECTURE

- How the codebase is organized at a high level
- The design patterns used (e.g. pipeline, agent loop, MVC)
- How data flows through the system from input to output:

  User Input → Module A → Module B → Module C → Final Output

- Why the code is structured this way — what problem does this 
  architecture solve?


SECTION 6 — KEY FILES EXPLANATION

This is the most detailed section. For every core file you read:

  ### filename.py
  **Purpose:** one sentence on what this file does

  Walk through each key function in the file:

  ### function_name()
  ```python
  # actual code snippet from the file — do not invent or paraphrase code
  ```
  - What this function does
  - Why it is implemented this way
  - How it connects to other parts of the project
  - Any non-obvious logic that needs explanation

Repeat for every core file. Do not skip files you read in Step 3.


SECTION 7 — EXAMPLE WORKFLOW

- Walk through one complete, concrete end-to-end example
- Use a real or realistic input (not "foo/bar" placeholders)
- Trace exactly what happens at each stage of the code:
  "When you run X, function Y is called, which does Z, then passes 
   the result to function W, which..."
- Show the intermediate states and the final output
- This section should make the reader feel like they watched the 
  code run in front of them


SECTION 8 — CUSTOMIZATION

- What can be changed without breaking the project
- Config values, hyperparameters, or flags the user can tweak
- How to swap components (e.g. replace the model, change the dataset)
- How to extend the project with new features
- Any hooks or extension points the author built in


SECTION 9 — TROUBLESHOOTING

- The most common errors a user will hit and exactly how to fix them
- Focus on errors tied to actual code you read — not generic advice
- Format each as:

  **Problem:** description of the error or symptom
  **Cause:** why it happens (reference the relevant code)
  **Fix:** exact steps to resolve it

QUALITY REQUIREMENTS:
- Follow the section order above exactly — do not reorder or merge sections
- Every claim about the code MUST reference actual code read via Navigate_repo
- Minimum 2000 words
- At least 5 actual code snippets from the repository — never invent code
- No guessing — if you did not read a file, do not reference it
- Write for an intermediate developer — technical but clear
'''

load_dotenv()
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

model = OpenAIChatCompletionsModel(
    model="gpt-4o-mini",
    openai_client=client)

tools=[get_readme, return_file_structure, Navigate_repo]
Parent_Agent=Agent(name='Parent Agent', instructions=parent_agent_instruction, tools=tools, model=model)

repo_markdown=[]

async def parent_agent(message : str):
    with trace('GitHub Repo Explainer'):
        result = Runner.run_streamed(starting_agent=Parent_Agent, input=message)
        async for event in result.stream_events():
            if event.type=='raw_response_event' and isinstance(event.data, ResponseTextDeltaEvent):
                print(event.data.delta, end='')
                repo_markdown.append(event.data.delta)

    tut_text=''.join(repo_markdown)
    console.print(Markdown(tut_text))
    save_as_pdf(tutorial_text=tut_text, filename=f'{uuid.uuid4()}.pdf')
    