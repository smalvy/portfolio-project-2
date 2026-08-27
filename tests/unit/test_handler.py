# Modified by smalvy, 2026 — adapted for portfolio-project-2
import json

import pytest
import os

from version_function import app
from unittest import mock


@pytest.fixture()
def event():
    """ Generates a Function URL Event"""

    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/my/path",
        "rawQueryString": "parameter1=value1&parameter1=value2&parameter2=value",
        "cookies": [
            "cookie1",
            "cookie2"
        ],
        "headers": {
            "header1": "value1",
            "header2": "value1,value2"
        },
        "queryStringParameters": {
            "parameter1": "value1,value2",
            "parameter2": "value"
        },
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "<urlid>",
            "authentication": None,
            "authorizer": {
                "iam": {
                        "accessKey": "AKIA...",
                        "accountId": "111122223333",
                        "callerId": "AIDA...",
                        "cognitoIdentity": None,
                        "principalOrgId": None,
                        "userArn": "arn:aws:iam::111122223333:user/example-user",
                        "userId": "AIDA..."
                }
            },
            "domainName": "<url-id>.lambda-url.us-west-2.on.aws",
            "domainPrefix": "<url-id>",
            "http": {
            "method": "POST",
            "path": "/my/path",
            "protocol": "HTTP/1.1",
            "sourceIp": "123.123.123.123",
            "userAgent": "agent"
            },
            "requestId": "id",
            "routeKey": "$default",
            "stage": "$default",
            "time": "12/Mar/2020:19:03:58 +0000",
            "timeEpoch": 1583348638390
        },
        "body": "Hello from client!",
        "pathParameters": None,
        "isBase64Encoded": False,
        "stageVariables": None
    }


@mock.patch.dict(os.environ, {}, clear=True)
def test_version_handler_default_env_values(event):

    ret = app.version_handler(event, "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200

    assert "message" in ret["body"]
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0

    assert "version" in ret["body"]
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0

    assert "commit_sha" in ret["body"]
    assert data["commit_sha"] == "unknown"

    assert "build_timestamp" in ret["body"]
    assert data["build_timestamp"] == "0001-01-01T00:00:00+00:00"


@mock.patch.dict(os.environ, {"COMMIT_SHA": "abc123-test", "BUILD_TIMESTAMP": "2026-08-20T00:00:00+00:00"})
def test_version_handler_with_env_values(event):

    ret = app.version_handler(event, "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200

    assert "message" in ret["body"]
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0

    assert "version" in ret["body"]
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0

    assert "commit_sha" in ret["body"]
    assert data["commit_sha"] == "abc123-test"

    assert "build_timestamp" in ret["body"]
    assert data["build_timestamp"] == "2026-08-20T00:00:00+00:00"
