# ROLL: A Gen AI-based app for adding flair to your auto-reply messages

ROLL, *Responsive and Outrageously Lively LLM-app*, is your digital courier that dutifully handles your Outlook inbox informing others whenever you're out of the office, busy in a meeting, or just taking a nap after lunch. Conceived while enjoying a delightful crisp Danish roll, the app is designed to add similar delight to your auto-reply messages.

## Getting Started

1. Ensure [pyenv](https://github.com/pyenv/pyenv) and [PDM](https://pdm.fming.dev/) are installed.

2. Install Python 3.11.*:

    ```bash
    pyenv install
    ```

3. Install the dependencies:

    ```bash
    pdm use python
    pdm run python -m ensurepip
    pdm install
    ```

4. Install the pre-commit hooks:

    ```bash
    pdm run pre-commit install
    ```

5. Use `.env.example` to create a `.env` file with the required environment variables.

6. Run the app:

    ```bash
    pdm run ui
    ```
