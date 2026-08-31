# Portfolio Project 2 — CI/CD Pipeline with Canary Lambda Deployments

> **Status: in progress.** This README currently documents the completed "target Lambda"
> milestone (a dedicated, canary-ready Lambda function with IAM-authenticated Function URL).
> The CI/CD pipeline itself (CodePipeline, CodeBuild, CodeDeploy) is the next milestone —
> see [Roadmap](#roadmap--status) below.

## Overview

This project builds a small AWS Lambda function designed specifically to demonstrate a
**canary deployment** pattern via AWS CodeDeploy: gradual traffic shifting between Lambda
versions, guarded by a pre-traffic validation hook and a CloudWatch alarm for automatic
rollback.

The function itself is intentionally minimal — it returns a JSON payload describing its
own build:

```json
{
  "message": "Hello from portfolio-project-2",
  "version": "1.0.0",
  "commit_sha": "unknown",
  "build_timestamp": "0001-01-01T00:00:00+00:00"
}
```

This is a deliberate design choice: the application logic is *not* the point of this
project — the deployment pipeline is. A trivial, observable payload makes it easy to prove
that a canary deployment is really shifting traffic between two versions (by calling the
Function URL repeatedly during a rollout and watching the response change), and gives the
pre-traffic hook something simple and fast to validate.

- `message` / `version` — static, human-edited fields, bumped manually on each release.
- `commit_sha` / `build_timestamp` — injected at build time by the CI/CD pipeline
  (`commit_sha` from CodeBuild's built-in `CODEBUILD_RESOLVED_SOURCE_VERSION`,
  `build_timestamp` generated explicitly in `buildspec.yml`). Until the pipeline exists,
  both default to fixed sentinel values (`"unknown"` and `"0001-01-01T00:00:00+00:00"`),
  matched exactly between the CloudFormation `Parameters` defaults and the Python fallback
  in `app.py`.

## Architecture

**Current milestone (this README):**

```
                Function URL (AuthType: AWS_IAM)
                        |
                        v
                VersionFunction (Lambda, Python)
                        |
                reads COMMIT_SHA / BUILD_TIMESTAMP
                from environment variables
```

Access to the Function URL is controlled by a **resource-based policy** (two
`AWS::Lambda::Permission` resources — one for `lambda:InvokeFunctionUrl`, one for
`lambda:InvokeFunction`, as required by the IAM authentication model for Lambda function
URLs), rather than an identity-based policy on the caller. This was a deliberate choice for
learning purposes — see [Security](#security-function-url-with-aws_iam) below.

**Planned (next milestone):** `AutoPublishAlias` + `DeploymentPreference` (canary
10%/5 minutes) via CodeDeploy, a pre-traffic hook Lambda that smoke-tests the new version
before any real traffic is shifted, and a CloudWatch alarm for automatic rollback — all
orchestrated by a CodePipeline (V2) triggered from GitHub via CodeStar Connections, with
CodeBuild handling build/test/package.

## Technologies

- AWS Lambda (Python 3.14, Zip package type)
- AWS Lambda Function URLs (`AWS_IAM` auth)
- AWS SAM (Infrastructure as Code)
- AWS IAM (resource-based policy on the function)
- LocalStack (local development)
- pytest + `unittest.mock` (unit tests), `boto3` + SigV4 (integration tests)

## Project structure

```
portfolio-project-2/
├── template.yaml               # SAM template: Lambda, Function URL, IAM permissions
├── version_function/
│   ├── app.py                  # Lambda handler
│   └── requirements.txt
├── tests/
│   ├── unit/
│   │   └── test_handler.py     # Mocked env vars, no AWS calls
│   └── integration/
│       └── test_version_function.py  # Calls the real deployed Function URL
├── samconfig.toml              # Deploy configs: `localstack` and AWS real environments
└── README.md
```

## Prerequisites

- AWS CLI configured with two profiles:
  - `localstack` — for local development
  - `portfolio-deployer` — dedicated IAM user (not root), least-privilege, for real
    AWS deploys
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Docker (required by LocalStack and by `sam build`/`sam local invoke`)
- LocalStack, with `samlocal` CLI wrapper (see
  [LocalStack SAM integration docs](https://docs.localstack.cloud/aws/integrations/aws-native-tools/sam-cli/))
- Python 3.14, `pip`

## Local development with LocalStack

Start LocalStack:

```bash
python -m localstack_cli.cli.main start   # PowerShell-friendly form of `localstack start`
```

Build and deploy against LocalStack:

```bash
sam build
samlocal deploy --config-env localstack
```

> **LocalStack limitation — please read before relying on local testing for security or
> canary behavior.** LocalStack's IAM Policy Enforcement (i.e., actually rejecting
> unauthenticated calls) is a paid-plan feature (Base/Ultimate), not available on the free
> Hobby plan used for this project. Locally, `AuthType: AWS_IAM` on the Function URL is
> accepted structurally, but **unauthenticated calls are not actually blocked**. Similarly,
> LocalStack's CodeDeploy support (used in the next milestone) is fully mocked: API calls
> succeed, but there is no real gradual traffic shifting or alarm-triggered rollback.
> LocalStack is used here to validate that the CloudFormation template deploys without
> structural errors, cheaply and quickly — **actual security and canary behavior are
> validated against real AWS**, documented below.

## Running the tests

Unit tests (mocked environment variables, no AWS calls required):

```bash
pytest tests/unit/ -v
```

Integration tests (require a **real, deployed** stack on AWS — see
[Deploying to AWS](#deploying-to-aws) below):

```bash
export AWS_SAM_STACK_NAME=portfolio-project-2
export AWS_PROFILE=portfolio-deployer
pytest tests/integration/ -v
```

The integration tests fetch the Function URL from the CloudFormation stack outputs and
verify both halves of the authentication story:

- an unsigned request returns `403 Forbidden`
- a request signed with AWS Signature Version 4 (SigV4), using the `portfolio-deployer`
  credentials, returns `200 OK` with the expected JSON payload

## Deploying to AWS

```bash
sam build
sam deploy --config-env portfolio-deployer
```

This requires the `portfolio-deployer` IAM user to have permission to manage the Lambda
execution role for this project (a dedicated custom IAM policy,
`IAMPolicyFor-portfolio-project-2`, scoped to `VersionFunctionRole`, following the same
least-privilege pattern used in
[Project 1](https://github.com/smalvy/portfolio-project-1)).

## Security: Function URL with `AWS_IAM`

The Function URL uses `AuthType: AWS_IAM` rather than `NONE`. For this specific use case —
a function that exposes only non-sensitive build metadata — `NONE` would have been a
perfectly reasonable and simpler choice. `AWS_IAM` was chosen deliberately, for the learning
value of working hands-on with SigV4 request signing and Lambda's dual authorization model
(identity-based *or* resource-based policy).

Concretely, this means:

- The function has an explicit **resource-based policy** (two `AWS::Lambda::Permission`
  resources) authorizing `portfolio-deployer` to call it — this is enough on its own, since
  for same-account callers AWS accepts *either* an identity-based policy *or* a
  resource-based policy (not necessarily both).
- Testing without a signature:
  ```bash
  curl -i <FunctionUrl>
  # → 403 Forbidden
  ```
- Testing with a valid signature, via [`awscurl`](https://github.com/okigan/awscurl):
  ```bash
  awscurl --service lambda --region <YOUR_AWS_REGION> --profile portfolio-deployer <FunctionUrl>
  # → 200 OK, JSON payload
  ```

## Cost & cleanup

Following the same cost-conscious approach as
[Project 1](https://github.com/smalvy/portfolio-project-1): this stack is intentionally
left running only while actively testing or preparing a demo, and torn down otherwise.

```bash
sam delete
```

By default, `sam delete` removes the CloudFormation stack and the deployed artifacts, but
**not** the S3 bucket used for packaging — it's kept and reused across deploys. To also
delete the bucket, pass `--s3-bucket <bucket-name>` explicitly.

## Roadmap / status

- [x] Target Lambda function with build metadata payload
- [x] Function URL with `AWS_IAM` authentication (resource-based policy)
- [x] Unit tests (mocked) and integration tests (real, signed requests)
- [x] Verified on real AWS: unauthenticated → 403, signed → 200
- [ ] `AutoPublishAlias` + `DeploymentPreference` (CodeDeploy canary)
- [ ] Pre-traffic hook (smoke test before traffic shifts)
- [ ] CloudWatch alarm for automatic rollback
- [ ] CodePipeline (V2) + CodeBuild + CodeDeploy, triggered from GitHub via CodeStar
      Connections
- [ ] SigV4 request-signing script (`scripts/`), for repeatable manual testing of the
      Function URL outside of pytest
