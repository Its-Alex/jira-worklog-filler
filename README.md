# Jira Worklog Filler

<!-- mdtoc -->

- [Introduction](#introduction)
- [Tutorials](#tutorials)
  - [Getting Started](#getting-started)
- [How-to guides](#how-to-guides)
  - [How to specify a custom date range](#how-to-specify-a-custom-date-range)
  - [How to generate a Jira API Token](#how-to-generate-a-jira-api-token)
  - [How to verify logs before applying](#how-to-verify-logs-before-applying)
- [Reference](#reference)
  - [CLI Options](#cli-options)
  - [Technical Requirements](#technical-requirements)
- [Explanation](#explanation)
  - [How it works](#how-it-works)
  - [Why Story Points?](#why-story-points)

<!-- numbering=false min=2 max=4 slug=github anchor=false link=true toc=true bullets=auto -->
<!-- /mdtoc -->

## Introduction

`fill_worklogs.py` is a productivity tool designed to automate the tedious
process of filling Jira worklogs. It identifies gaps in your daily 8-hour
schedule and suggests "In Progress" tasks to fill those gaps based on your
activity and story points.

## Tutorials

### Getting Started

Follow these steps to set up the script for the first time:

1. **Install Poetry**: If you haven't already, install
   [Poetry](https://python-poetry.org/docs/#installation). This can be done using
   [mise](https://mise.jdx.dev/):

    ```bash
    mise install
     ```
2. **Install Dependencies**:

    ```bash
    poetry install
    ```

3. **Configure Environment**: Create a `.env` file or export the following
   variables:

    ```bash
    export JIRA_SERVER="https://your-domain.atlassian.net/"
    export JIRA_EMAIL="your-email@company.com"
    export JIRA_API_TOKEN="your-jira-api-token"
    ```

4. **Run a Dry Run**:
    Execute the script for the last 3 days (default) to see what it would log:

    ```bash
    poetry run python fill_worklogs.py
    ```

    Alternatively, you can use the shortcut defined in `pyproject.toml`:

    ```bash
    poetry run fill-worklogs
    ```

## How-to guides

### How to specify a custom date range

You can define a specific window using the `--start-date` and `--end-date` options:

```bash
poetry run fill-worklogs --start-date 2023-10-01 --end-date 2023-10-05
```

### How to generate a Jira API Token

1. Log in to [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens).
2. Click **Create API token**.
3. Copy the token and save it in your `JIRA_API_TOKEN` environment variable.

### How to verify logs before applying

The script always displays a table of proposed worklogs and asks for confirmation (`[y/N]`) before making any changes to Jira.

## Reference

### CLI Options

| Option | Env Var | Default | Description |
| --- | --- | --- | --- |
| `--start-date` | - | Today - 3 days | Start date for checking worklogs (YYYY-MM-DD). |
| `--end-date` | - | Today | End date for checking worklogs (YYYY-MM-DD). |
| `--jira-server` | `JIRA_SERVER` | `https://xxii...` | Your Jira instance URL. |
| `--jira-email` | `JIRA_EMAIL` | `arthur...` | Your Jira account email. |
| `--jira-api-token` | `JIRA_API_TOKEN` | **Required** | Your Jira API Token. |

### Technical Requirements

- **Python**: >= 3.11
- **Libraries**: `jira`, `typer` see [pyproject.toml](pyproject.toml)

## Explanation

### How it works

1. **Aggregation**: The script fetches all worklogs authored by the current user within the specified date range.
2. **Gap Detection**: It calculates the total time logged per day. If a weekday has less than 8 hours, it marks it as a "Missing Day".
3. **Issue Selection**: For each missing day, it searches for issues that were "In Progress" and assigned to you on that specific date.
4. **Proportional Distribution**: The missing hours are distributed across all "In Progress" issues proportionally to their **Story Points** (customfield_10117, defaults to 1 if unset). For example, if you have 4 missing hours and two issues with 3 and 1 story points, they receive 3h and 1h respectively.
5. **Logging**: Once confirmed, it adds the computed duration to each selected issue, starting at 09:30 AM (Europe/Paris time).

### Why Story Points?

The script uses story points as a proxy for effort distribution — tasks with higher story points receive a proportionally larger share of your "untracked" time during a day.
