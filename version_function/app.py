# Modified by smalvy, 2026 — adapted for portfolio-project-2
import json
import os
import datetime as dt


def version_handler(event, context):

    def get_default_timestamp():
        default_timestamp = dt.datetime(1, 1, 1, tzinfo=dt.timezone.utc)
        return default_timestamp.isoformat()

    # this value must match the default value assigned to the parameter CommitShaValue inside template.yaml file
    commit_sha = os.environ.get("COMMIT_SHA", "unknown")
    # this value must match the default value assigned to the parameter BuildTimestampValue inside template.yaml file
    build_timestamp = os.environ.get("BUILD_TIMESTAMP") or get_default_timestamp()

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Hello from portfolio-project-2",
            "version": "1.0.0",
            "commit_sha": commit_sha,
            "build_timestamp": build_timestamp,
        }),
    }
