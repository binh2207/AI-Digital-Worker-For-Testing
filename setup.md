# Quality-Engineer-Bot — Setup Guide

## 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

## 2. Configure environment

Copy `.env.example` to `.env` and fill in every value:

| Variable | Description |
|---|---|
| `SLACK_APP_TOKEN` | App-Level token (xapp-…) — enables Socket Mode |
| `SLACK_BOT_TOKEN` | Bot User OAuth token (xoxb-…) |
| `JIRA_URL` | e.g. `https://your-domain.atlassian.net` |
| `JIRA_USER` | Your Atlassian account email |
| `JIRA_API_TOKEN` | Generate at https://id.atlassian.com/manage-profile/security/api-tokens |
| `JIRA_PROJECT_KEY` | e.g. `PROJ` |
| `JIRA_REVIEW_COLUMN` | Exact status name in your board, e.g. `In Review` |
| `OPENAI_API_KEY` | Your OpenAI key |
| `OPENAI_MODEL` | Defaults to `gpt-4o` |
| `PLAYWRIGHT_BASE_URL` | Base URL of the app under test (default: `https://sauce-demo.myshopify.com`) |
| `PLAYWRIGHT_TESTS_DIR` | Where generated `.spec.ts` files are written |

## 3. Slack App settings

In your Slack App dashboard:
- **Socket Mode** → Enable
- **Event Subscriptions** → Enable, subscribe to `app_mention`
- **OAuth Scopes** (Bot): `app_mentions:read`, `chat:write`, `channels:history`

## 4. Run

```bash
python main.py
```

## 5. Trigger

In any Slack channel where the bot is invited:

```
@Quality-Engineer-Bot check the JIRA board
```

## Workflow

```
Slack mention
     │
     ▼
[fetch_tickets]  ── JIRA: get all "In Review" tickets
     │
     ▼
[test_designer]  ── LLM reads SRS → generates Playwright TypeScript tests
     │               Posts test code as JIRA comment
     ▼
[test_executor]  ── Writes .spec.ts files → npx playwright test
     │               Captures JSON report
     ▼
[test_reporter]  ── LLM summarises results
                     Updates JIRA status (Done / In Progress)
                     Posts full report to Slack thread
```
