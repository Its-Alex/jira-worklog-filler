from typing import Annotated, NamedTuple
import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
import typer
import jira

load_dotenv()

app = typer.Typer()


class WorklogToApply(NamedTuple):
    date: date
    hours: float
    issue_key: str

class MissingDay(NamedTuple):
    date: date
    missing_hours: float


@app.command()
def main(
    start_date_str: Annotated[str, typer.Option("--start-date", help="Start date (YYYY-MM-DD)")] = str(date.today() - timedelta(days=3)),
    end_date_str: Annotated[str, typer.Option("--end-date", help="End date (YYYY-MM-DD)")] = str(date.today()),
    jira_server: Annotated[str, typer.Option(envvar="JIRA_SERVER")] = "https://xxiigroup.atlassian.net/",
    jira_email: Annotated[str, typer.Option(envvar="JIRA_EMAIL")] = "arthur.vinot@xxii.fr",
    jira_api_token: Annotated[str, typer.Option(envvar="JIRA_API_TOKEN")] = ...,
):
    jira_client = jira.JIRA(server=jira_server, basic_auth=(jira_email, jira_api_token))

    start_date = date.fromisoformat(start_date_str)
    end_date = date.fromisoformat(end_date_str)

    # 1. We search for issues that have worklogs by the user in the range
    issues = jira_client.search_issues(
        jql_str=f"worklogDate >= '{start_date}' AND worklogDate <= '{end_date}' AND worklogAuthor = currentUser()",
        maxResults=1000
    )
    # Note: Even if no issues are found, we might still have missing days to fill.

    date_to_worklog_seconds: dict[date, int] = {}

    for issue in issues:
        # Get worklogs for this issue
        issue_worklogs: list[jira.Worklog] = jira_client.worklogs(issue.key)

        for issue_worklog in issue_worklogs:
            author_email = getattr(issue_worklog.author, "emailAddress", None)  # None handles deleted user
            if author_email == jira_email:
                worklog_started_date = datetime.fromisoformat(issue_worklog.started).date()
                if start_date <= worklog_started_date <= end_date:
                    date_to_worklog_seconds.setdefault(worklog_started_date, 0)
                    date_to_worklog_seconds[worklog_started_date] += issue_worklog.timeSpentSeconds

    # 2. Identify missing days
    date_iterator = start_date

    missing_days = []
    while date_iterator <= end_date:
        # Weekdays only (0-4 are Mon-Fri)
        if date_iterator.weekday() < 5:
            total_seconds = date_to_worklog_seconds.get(date_iterator, 0)
            if total_seconds < 8 * 3600:
                missing_hours = 8 - total_seconds / 3600
                missing_days.append(
                    MissingDay(date_iterator, missing_hours)
                )
        date_iterator += timedelta(days=1)

    # 3. Find "In Progress" issues to fill the gap
    print("| Date | Missing Time (h) | Issue | Pts | Logged (h) | Description |")
    print("| --- | --- | --- | --- | --- | --- |")

    worklogs_to_apply: list[WorklogToApply] = []

    ignored_titles = {
        "Maintien opérationnel & Support interne",
        "Atelier technique & Préparation du sprint",
    }

    # Fix seed for deterministic random choice
    random.seed(22)

    for day in missing_days:
        # Find issues that were in progress on this specific day
        # JQL: status WAS "In Progress" ON "date"
        in_progress_issues = jira_client.search_issues(
            f'status WAS "In Progress" ON "{day.date}" AND assignee WAS currentUser() ON "{day.date}" AND type IN (Task, Story, "New Feature", Bug, Sub-task)'
        )

        in_progress_issues = [
            issue for issue in in_progress_issues
            if not any(title in issue.fields.summary for title in ignored_titles)
        ]

        if in_progress_issues:
            # NOTE: customfield_10117 == Story points
            # We log time proportionally to story points. Default to 1 if not set.
            issue_points = []
            total_points = 0
            for issue in in_progress_issues:
                pts = getattr(issue.fields, "customfield_10117", 1) or 1
                issue_points.append((issue, pts))
                total_points += pts

            for issue, pts in issue_points:
                hours_to_log = day.missing_hours * (pts / total_points)
                
                print(
                    f"| {day.date} | {day.missing_hours:.2f} | {issue.key} | {pts} | {hours_to_log:.2f} | {issue.fields.summary} |"
                )
                worklogs_to_apply.append(WorklogToApply(day.date, hours_to_log, issue.key))
        else:
            print(
                f"| {day.date} | {day.missing_hours:.2f} | N/A | - | - | No In Progress issue found for this day |"
            )

    if not worklogs_to_apply:
        print("\nNo worklogs to apply.")
        return

    if not typer.confirm("Do you want to apply these changes?", default=False):
        print("Aborted.")
        return

    print("\nApplying worklogs...")
    for worklog in worklogs_to_apply:
        print(f"Adding {worklog.hours:.2f}h to {worklog.issue_key} on {worklog.date}...")
        jira_client.add_worklog(
            issue=worklog.issue_key,
            timeSpentSeconds=round(worklog.hours * 3600),
            started=datetime.combine(worklog.date, time(9, 30, tzinfo=ZoneInfo("Europe/Paris")))
        )
    print("Done!")


if __name__ == "__main__":
    app()
