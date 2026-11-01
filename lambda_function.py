import csv
import io
import os
import time
from datetime import datetime, timezone

import boto3

STALE_DAYS = int(os.environ.get("STALE_DAYS", "90"))
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")  # not set = just print

# Values AWS uses in the report when there's no real date
NO_DATE = {"N/A", "no_information", "not_supported", ""}


def get_credential_report(iam):
    """Ask AWS to build the report, wait until it's ready, return rows as dicts."""
    while iam.generate_credential_report()["State"] != "COMPLETE":
        time.sleep(2)
    content = iam.get_credential_report()["Content"]  # boto3 returns raw CSV bytes
    return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))


def parse_date(value):
    """Turn a report timestamp into a datetime, or None if there isn't one."""
    if value in NO_DATE:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def days_since(dt, now):
    return (now - dt).days


def find_issues(rows, now, stale_days=STALE_DAYS):
    """Return a list of human-readable findings."""
    issues = []
    for row in rows:
        user = row["user"]
        if user == "<root_account>" or user == "TestUnusedSvc" :
            continue  # root is reviewed separately

        created = parse_date(row["user_creation_time"])

        # Console password
        if row["password_enabled"] == "true":
            last = parse_date(row["password_last_used"])
            ref = last or created  # never logged in -> measure from account creation
            age = days_since(ref, now)
            if age >= stale_days:
                how = f"last used {age} days ago" if last else f"never used, created {age} days ago"
                issues.append(f"{user}: console password {how}")
            if row["mfa_active"] != "true":
                issues.append(f"{user}: console access without MFA")

        # Access keys 1 and 2
        for n in ("1", "2"):
            if row[f"access_key_{n}_active"] != "true":
                continue
            last = parse_date(row[f"access_key_{n}_last_used_date"])
            ref = last or parse_date(row[f"access_key_{n}_last_rotated"])
            age = days_since(ref, now)
            if age >= stale_days:
                how = f"last used {age} days ago" if last else f"never used, created {age} days ago"
                issues.append(f"{user}: access key {n} {how}")
            created = parse_date(row[f"access_key_{n}_last_rotated"])
            key_age = days_since(created, now)
            if key_age >= 90:
               issues.append(f"{user}: access key {n} is {key_age} days old, please rotate it")
    return issues


def build_message(issues, stale_days=STALE_DAYS):
    if not issues:
        return f"No IAM credentials unused for {stale_days}+ days, and all console users have MFA."
    lines = [f"IAM access review: {len(issues)} finding(s) (threshold {stale_days} days)", ""]
    lines += [f"- {i}" for i in issues]
    lines += ["", "Review each one: disable or delete credentials that are no longer needed."]
    return "\n".join(lines)


def lambda_handler(event=None, context=None):
    iam = boto3.client("iam")
    rows = get_credential_report(iam)
    issues = find_issues(rows, datetime.now(timezone.utc))
    message = build_message(issues)

    print(message)  # your terminal locally, CloudWatch Logs on Lambda
    if SNS_TOPIC_ARN:
        boto3.client("sns").publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"IAM access review: {len(issues)} finding(s)",
            Message=message,
        )
    return {"findings": len(issues)}


if __name__ == "__main__":
    lambda_handler()
