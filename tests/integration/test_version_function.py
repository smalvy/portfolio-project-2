# Modified by smalvy, 2026 — adapted for portfolio-project-2
import os

import boto3
import pytest
import requests
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth

"""
Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test. 
"""


class TestVersionFunction:

    @pytest.fixture()
    def version_function_url(self):
        """ Get the Version Lambda Function URL from Cloudformation Stack outputs """
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")
        profile_name = os.environ.get("AWS_PROFILE")
        cloudformation_endpoint = os.environ.get("CLOUDFORMATION_ENDPOINT") or None

        if stack_name is None:
            raise ValueError('Please set the AWS_SAM_STACK_NAME environment variable to the name of your stack')

        if profile_name is None:
            raise ValueError('Please set the AWS_PROFILE environment variable to the name of your profile')

        session = boto3.Session(profile_name=profile_name)
        client = session.client("cloudformation", endpoint_url=cloudformation_endpoint)

        try:
            response = client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name} \n" f'Please make sure a stack with the name "{stack_name}" exists'
            ) from e

        stacks = response["Stacks"]
        stack_outputs = stacks[0]["Outputs"]
        version_function_outputs = [output for output in stack_outputs if output["OutputKey"] == "VersionFunctionUrl"]

        if not version_function_outputs:
            raise KeyError(f"VersionFunctionUrl not found in stack {stack_name}")

        return version_function_outputs[0]["OutputValue"]  # Extract Version function URL from stack outputs


    def test_call_without_sigv4(self, version_function_url):
        """ Call the Version Lambda function URL not using AWS Signature Version 4 and check the response """
        response = requests.get(version_function_url)

        assert response.status_code == 403
        assert response.json() == {"Message": "Forbidden"}


    def test_call_with_sigv4(self, version_function_url):
        """ Call the Version Lambda function URL using AWS Signature Version 4 and check the response """
        profile = os.environ.get("AWS_PROFILE")
        service = "lambda"
        method = "GET"

        session = boto3.Session(profile_name=profile)

        request = AWSRequest(method, version_function_url)

        SigV4Auth(session.get_credentials(), service, session.region_name).add_auth(request)

        response = requests.request(method, version_function_url, headers=dict(request.headers))
        body = response.json()

        assert response.status_code == 200

        assert "message" in body.keys()
        assert isinstance(body["message"], str)
        assert len(body["message"]) > 0

        assert "version" in body.keys()
        assert isinstance(body["version"], str)
        assert len(body["version"]) > 0

        assert "commit_sha" in body.keys()
        assert body["commit_sha"] == "unknown" # modify this test when COMMIT_SHA variable will be passed by the pipeline

        assert "build_timestamp" in body.keys()
        assert body["build_timestamp"] == "0001-01-01T00:00:00+00:00" # modify this test when BUILD_TIMESTAMP variable will be passed by the pipeline
