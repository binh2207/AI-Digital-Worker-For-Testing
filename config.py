import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

PROJECT_DIR = str(Path(__file__).parent)

# Resolve Claude Code CLI path:
#   1. Explicit override via env var (useful in CI)
#   2. Auto-detected from PATH (works on Linux/Mac after `npm install -g`)
#   3. Windows fallback (local dev machine)
CLAUDE_CMD = (
    os.environ.get("CLAUDE_CMD")
    or shutil.which("claude")
    or r"C:\Users\OS\AppData\Roaming\npm\claude.cmd"
)

SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")   # only needed for local Socket Mode bot
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")

JIRA_URL = os.environ["JIRA_URL"]
JIRA_USER = os.environ["JIRA_USER"]
JIRA_API_TOKEN = os.environ["JIRA_API_TOKEN"]
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "")
JIRA_REVIEW_COLUMN = os.environ.get("JIRA_REVIEW_COLUMN", "In Review")

PLAYWRIGHT_BASE_URL = os.environ.get("PLAYWRIGHT_BASE_URL", "https://sauce-demo.myshopify.com")

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ["GITHUB_REPO"]          # "owner/repo-name"
GITHUB_DEFAULT_BRANCH = os.environ.get("GITHUB_DEFAULT_BRANCH", "main")
