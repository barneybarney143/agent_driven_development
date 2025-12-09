# Ollama Setup Instructions

This project uses [Ollama](https://ollama.com/) to run local LLMs (specifically `llama3:8b`) if a Gemini API key is not provided.

## 1. Install Ollama Application (Server)

**Crucial:** You must install the Ollama *application*, not just the Python library. The application acts as the server that hosts the models.

### Windows
You can install via `winget` (recommended) or download the installer from the website.

**Terminal (PowerShell/CMD):**
```powershell
winget install Ollama.Ollama
```
*Note: After installation, you may need to restart your terminal or IDE for the `ollama` command to be available in your PATH.*

### macOS / Linux
Follow the instructions on [ollama.com/download](https://ollama.com/download).
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## 2. Verify Installation

Open a terminal and run:
```bash
ollama --version
```
If you see a version number (e.g., `ollama version 0.1.20`), the server is installed correctly.

## 3. Python Dependencies

The Python client library is included in `requirements.txt`:
```bash
pip install -r requirements.txt
```

## 4. Running the Project

When you run the main script:
```bash
python autogen_tdd_crew.py
```

The script includes logic to:
1.  Check if `ollama` is in your PATH (and attempt to add the default Windows path if missing).
2.  Check if the required model (`llama3:8b`) is available.
3.  **Automatically pull (download)** the model if it is missing.

*Note: The first run may take some time to download the model (approx. 4.7 GB).*
