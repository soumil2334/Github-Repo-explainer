# %%
import requests
import base64

url1= "https://api.github.com/repos/zju3dv/pvnet/contents/run.py?ref=master"
response = requests.get(url1)

data = response.json()
encoded_content = data['content']
decoded_content = base64.b64decode(encoded_content).decode("utf-8")
print(decoded_content)

# %%
import requests
import base64

url1= "https://api.github.com/repos/zju3dv/pvnet/contents/"
response = requests.get(url1)

data=response.json()
print(data)
for content in data:
    if content=='content':
        print(True)
    print(content)


# %%
import requests
import base64

url1= "https://api.github.com/repos/zju3dv/pvnet/contents/assets/cat.png?ref=master"
response = requests.get(url1)

data=response.json()
for content in data:
    if content=='content':
        print(data['content'])
        print(True)
    print(content)

# %%
from pydantic import BaseModel, Field
from typing import Optional
import base64
from agents import Agent, Runner, trace, OpenAIChatCompletionsModel, function_tool
import os

github_access_token=os.getenv('Github_access_token')
HEADERS = {"Authorization": github_access_token}

class Navigate_repo_class(BaseModel):
    list_url: Optional[list[dict]]
    content : Optional[str]

@function_tool
def Navigate_repo(url:str, file_type : str)-> Navigate_repo_class:
    '''
    When to call this function->
    One you have to navigate a tree or to get the content of blob

    What to pass in this function->
    1. url : GitHub API contents URL only. Must follow this format:
         https://api.github.com/repos/{user}/{repo}/contents/{path}
         
         NOT the HTML url (https://github.com/...) 
         Use URLs returned by return_file_structure or previous Navigate_repo calls.
         Never construct URLs manually.

    2. file_type : the type of the file the url is pointing towards (blob/tree)
    
    What does the function return->
    list_url : list of the child URLs present within the given url
    content : if the url file_type is a blob then return the content

    What to do next after calling this function->
    file_type='tree' → make parallel Navigate_repo calls on each URL in list_url
    file_type='blob' → pass content to the Parent agent, continue remaining trees
    '''


    response=requests.get(url, headers=HEADERS)
    Data=response.json()
    
    content=None
    response_list=[]

    if file_type=='tree':
        for data in Data:
            response_list.append({'name' : data.get('name'), 'URL' : data.get('url')})

    if file_type=='blob':
        content=base64.b64decode(Data['content']).decode("utf-8")

    return Navigate_repo_class(list_url=response_list, content=content)

@function_tool
def return_file_structure(user: str, repository_name:str):
    '''
    When to call this function->
    After reading the Readme of the repository to understand the repository structure

    What to pass in this function->
    1. user : owner of the repository
    2. repository_name : repository name as given on GitHub
    
    What does the function return->
    returns the string of the repository structure e.g. (Readme.md Blob \n asset tree)

    What to do next after calling this function->
    Use the tool Navigate_repo to explore and understand the repo
    '''

    repo_url=f'https://api.github.com/repos/{user}/{repository_name}/git/trees/master?recursive=1'
    
    response=requests.get(repo_url, headers=HEADERS)
    data=response.json() 

    structure_string=''

    for item in data["tree"]:
        structure_string+=f'''{item['path']}  {item['type']} \n'''

    return structure_string

@function_tool
def get_readme(user:str, repository_name:str):
    '''
    When to call->
    Always call this FIRST before any other tool.

    What to pass in->
    1. user : GitHub username or org name e.g. (https://github.com/zju3dv/pvnet here name is zju3dv)
    2. repository_name : exact repository name as on GitHub e.g. (https://github.com/zju3dv/pvnet here repository_name is pvnet)

    What does it return->
    str : full decoded README content, or 'Readme not found' if absent.

    What to do next->
    Call return_file_structure to map the full repo, using README 
    as context for which files matter.    
    '''

    url=f'''https://api.github.com/repos/{user}/{repository_name}/contents/'''

    response=requests.get(url, headers=HEADERS)

    Data=response.json()

    content='Readme not found'
    for data in Data:
        readme_check=data['name'].lower()
        if readme_check=='readme.md':
            url=data['url']
            result=requests.get(url)
            result=result.json()
            content=result['content']
            content=base64.b64decode(content).decode("utf-8")

    return content

result=get_readme(user='soumil2334', repository_name='Youtube-Ask-Feature')

# %%
parent_agent_instruction='''
You are a technical educator who creates in-depth tutorials for GitHub repositories.
You have three tools available to explore a repository. You MUST follow this exact 
workflow — do not skip any step.

═══════════════════════════════════════
STEP 1 — Read the README (MANDATORY FIRST STEP)
═══════════════════════════════════════
Call get_readme() first, always.
- Understand the project's purpose, architecture, and key components.
- Note every major feature, library, and module mentioned.
- This is your reference map for all subsequent decisions.

═══════════════════════════════════════
STEP 2 — Get the full file structure (MANDATORY SECOND STEP)
═══════════════════════════════════════
Call return_file_structure() immediately after reading the README.
- Study every path and identify which trees and blobs are relevant.
- Mark ALL files that likely contain core logic based on the README.
- Do NOT proceed to Step 3 until you have a clear picture of what to explore.

═══════════════════════════════════════
STEP 3 — Navigate and read ALL relevant files (MANDATORY — DO NOT SKIP)
═══════════════════════════════════════
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

e) Continue until you have read ALL files core to understanding the project.
   Do not stop after 1-2 files. A thorough exploration means reading 
   at minimum every file that contributes to the core functionality.

YOU MUST NOT MOVE TO STEP 4 UNTIL YOU HAVE CALLED Navigate_repo() 
AT LEAST ONCE AND READ THE CORE FILES.

═══════════════════════════════════════
STEP 4 — Write the tutorial (ONLY after Step 3 is complete)
═══════════════════════════════════════
Write a tutorial of AT LEAST 2000 words covering:

1. PROJECT OVERVIEW
   - What problem does this project solve?
   - What is the high-level architecture?
   - What libraries are used and WHY was each chosen?

2. SETUP & PREREQUISITES
   - Dependencies from requirements.txt
   - Environment variables or configuration needed
   - How to install and run

3. CODE WALKTHROUGH (this is the core section — must be detailed)
   - Walk through the code file by file, function by function
   - For every key function, include the actual code snippet and explain:
     * What it does
     * Why it's implemented this way
     * How it connects to the rest of the project
   - Use this format for every code snippet:
     
     ### Function/File Name
```python
     # actual code from the repo
```
     Explanation of what this code does and why...

4. HOW IT ALL CONNECTS
   - Trace the full flow from user input to final output
   - Show how each module hands off to the next

5. KEY DESIGN DECISIONS
   - Why specific libraries were chosen
   - Any notable patterns or architectural decisions

6. CONCLUSION
   - Summary of what the project achieves
   - Potential improvements or extensions

QUALITY REQUIREMENTS:
- Every claim about the code MUST reference actual code you read via Navigate_repo
- Minimum 20000 words
- At least 5 code snippets from the actual repository
- No guessing — if you didn't read a file, don't reference it
""",
    tools=[get_readme, return_file_structure, Navigate_repo]
)
'''

# %%
import os
import openai
from openai import AsyncOpenAI
from dotenv import load_dotenv
from openai.types.responses import ResponseTextDeltaEvent

# %%
load_dotenv()
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

model = OpenAIChatCompletionsModel(
    model="gpt-4o-mini",
    openai_client=client)

tools=[get_readme, return_file_structure, Navigate_repo]
Parent_Agent=Agent(name='Parent Agent', instructions=parent_agent_instruction, tools=tools, model=model)

message='explain this repo https://github.com/zju3dv/pvnet'

with trace('GitHub Repo Explainer'):
    result = Runner.run_streamed(starting_agent=Parent_Agent, input=message)
    async for event in result.stream_events():
        if event.type=='raw_response_event' and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end='')

# %%



