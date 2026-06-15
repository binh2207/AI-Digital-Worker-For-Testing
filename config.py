import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

PROJECT_DIR = str(Path(__file__).parent)
CLAUDE_CMD = r"C:\Users\OS\AppData\Roaming\npm\claude.cmd"

SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]

JIRA_URL = os.environ["JIRA_URL"]
JIRA_USER = os.environ["JIRA_USER"]
JIRA_API_TOKEN = os.environ["JIRA_API_TOKEN"]
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "")
JIRA_REVIEW_COLUMN = os.environ.get("JIRA_REVIEW_COLUMN", "In Review")

PLAYWRIGHT_BASE_URL = os.environ.get("PLAYWRIGHT_BASE_URL", "https://sauce-demo.myshopify.com")
