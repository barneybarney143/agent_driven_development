import os
import sys
import subprocess
import platform
import autogen
from typing import Dict
from dotenv import load_dotenv

load_dotenv()


def check_and_pull_ollama_model(model_name: str = "llama3:8b"):
    """Checks if the Ollama model exists, pulls it if not."""

    # OS-Specific Path Setup
    current_os = platform.system()
    if current_os == "Windows":
        # Dynamic path to Local AppData
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            ollama_path = os.path.join(local_app_data, "Programs", "Ollama")
            # Add to PATH if it exists and not already there
            if os.path.exists(ollama_path) and ollama_path not in os.environ["PATH"]:
                print(f"Adding {ollama_path} to PATH...")
                os.environ["PATH"] += os.pathsep + ollama_path

    try:
        # Check if model exists
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if model_name not in result.stdout:
            print(f"Model {model_name} not found. Pulling...")
            subprocess.run(["ollama", "pull", model_name], check=True)
            print(f"Model {model_name} pulled successfully.")
        else:
            print(f"Model {model_name} found.")
    except FileNotFoundError:
        print(
            "Error: 'ollama' command not found. Please ensure Ollama is installed and in your PATH."
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error pulling model: {e}")
        sys.exit(1)


def get_llm_config() -> Dict:
    """Returns the LLM configuration based on environment variables."""
    api_key = os.environ.get("GEMINI_API_KEY")

    if api_key:
        print("Using Gemini 2.5 Flash configuration.")
        return {
            "config_list": [
                {"model": "gemini-2.5-flash", "api_key": api_key, "api_type": "google"}
            ],
            "temperature": 0.2,  # Lower temperature for coding/TDD
            "seed": 42,
        }
    else:
        print("GEMINI_API_KEY not found. Falling back to local Ollama.")
        model = "llama3:8b"
        check_and_pull_ollama_model(model)
        return {
            "config_list": [
                {
                    "model": model,
                    "base_url": "http://localhost:11434/v1",
                    "api_key": "ollama",  # Required placeholder
                }
            ],
            "temperature": 0.2,
            "seed": 42,
            "request_timeout": 300,  # Increased timeout for local execution
        }


llm_config = get_llm_config()


# --- Custom Agent Classes ---

class CleanUserProxyAgent(autogen.UserProxyAgent):
    """A UserProxyAgent with a cleaner UI prompt."""
    def get_human_input(self, prompt: str) -> str:
        # Ignore the verbose default prompt
        custom_prompt = (
            "\n"
            "   [ENTER] Run Code / Approve\n"
            "   [Type]  Give Instructions\n"
            "   [exit]  Quit\n"
            "> "
        )
        return input(custom_prompt)

# --- Agent Definitions ---

# Planner: Defines the TDD steps.
planner = autogen.AssistantAgent(
    name="Planner",
    system_message="""You are an expert Software Architect and Project Planner.
    Your goal is to guide the TDD process.
    1. Analyze the user's initial request.
    2. Break it down into small, testable TDD tasks.
    3. Instruct the 'Tester' to write a FAILING test for the *next* small step.
    4. Do not write code or tests yourself.
    5. Ends your message by explicitly naming the next speaker, e.g., "Tester, write a test for [feature]."
    """,
    llm_config=llm_config,
)

# Tester: Writes tests.
tester = autogen.AssistantAgent(
    name="Tester",
    system_message="""You are a QA Automation Engineer specialized in TDD using pytest.
    Your goal is to write robust test cases.
    1. Receive instructions from the Planner.
    2. Write a comprehensive test suite for the requested feature.
    3. Ensure the test INITIALLY FAILS (Red phase).
    4. Save the test to 'tests/test_app.py' by outputting a PYTHON BLOCK that writes the file.
       Example:
       ```python
       with open('tests/test_app.py', 'w') as f:
           f.write('''...code...''')
       ```
    5. Do NOT just list the code. You must WRITE it to disk.
    6. Always aim for 100% code coverage.
    7. Ends your message by explicitly calling the Executor: "Executor, please run this test."
    """,
    llm_config=llm_config,
)

# Coder: Writes implementation code.
coder = autogen.AssistantAgent(
    name="Coder",
    system_message="""You are a Senior Python Developer.
    Your goal is to write clean, efficient implementation code.
    1. Read the failing test and errors provided.
    2. Write the MINIMUM amount of code in 'src/app.py' to pass the test (Green phase).
    3. Save the code to 'src/app.py' by outputting a PYTHON BLOCK that writes the file.
       Example:
       ```python
       with open('src/app.py', 'w') as f:
           f.write('''...code...''')
       ```
    4. Do not over-engineer.
    5. If the Linter reports issues, fix them immediately.
    6. Ends your message by explicitly calling the Executor: "Executor, verify this fix."
    """,
    llm_config=llm_config,
)

# Linter: Checks style.
linter = autogen.AssistantAgent(
    name="Linter",
    system_message="""You are a Code Quality Guardian.
    Your goal is to ensure PEP8 compliance and code quality.
    1. After the Coder updates the code (and tests pass), analyze the codebase.
    2. If there are style violations (flake8), strictly list them and instruct the Coder to fix.
    3. If the code is clean, approve it and inform the Planner.
    4. Ends your message by explicitly naming the next speaker: 
       - "Coder, fix these style issues." (if issues found)
       - "Planner, the code is clean and tested." (if success)
    """,
    llm_config=llm_config,
)

# Executor: Runs commands.
executor = CleanUserProxyAgent(
    name="Executor",
    system_message="""You are the build server and execution environment.
    1. You execute python scripts, pytest commands, and linter checks.
    2. Working directory: '.', but code is in 'src/' and 'tests/'.
    3. When ANY agent provides code blocks (bash or python), execute them.
    4. Report the stdout and stderr back to the chat.
    5. Specifically run: `pytest --cov=src tests/` to check functionality and coverage.
    6. Run: `flake8 src/ tests/` to check style.
    7. After execution, analyze the output and direct the flow:
       - If tests FAILED: "Coder, please fix the errors."
       - If tests PASSED: "Linter, please check the style."
       - If lint FAILED: "Coder, please fix the style."
    """,
    # ACTIVATING GUARDRAILS: Always ask for human input before proceeding/executing.
    # The user must press Enter to approve, or type instructions to override.
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={
        "work_dir": ".",
        "use_docker": False,  # Running locally
    },
)

# --- Group Chat Flow ---


groupchat = autogen.GroupChat(
    agents=[planner, tester, coder, linter, executor],
    messages=[],
    max_round=50,
)

manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# --- Start ---

initial_task = "Start the development. Create a Python class that calculates the sum of even numbers in a list. Ensure 100% test coverage."

print("Starting TDD Agents...")
executor.initiate_chat(manager, message=initial_task)
