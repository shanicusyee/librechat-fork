# Requirements Document

## Introduction

This feature delivers an end-to-end demonstration of a CI/CD evidence collection pipeline. A simple chat application, built using Libre.Chat, is deployed to AWS infrastructure provisioned via Terraform. The user's GitHub repository is a **fork of danny-avila/LibreChat**, containing the full LibreChat source code alongside evidence-pipeline additions (`evidence_agent/`, `terraform/`, `.github/workflows/`, `librechat.yaml`). A GitHub Actions pipeline triggers on merge to the main branch, running the application through build, test, and deployment stages. A key pipeline stage uses Amazon Bedrock AgentCore Browser to launch a headless browser session against the deployed application, capture screenshots and test reports as compliance evidence, and store those artifacts in an Amazon S3 bucket.

## Glossary

- **Chat_Application**: A lightweight, real-time messaging web application built using Libre.Chat (maintained as a fork of danny-avila/LibreChat), deployed as the system under demonstration.
- **Pipeline**: A GitHub Actions CI/CD workflow that automates build, test, deployment, and evidence collection stages.
- **Evidence_Agent**: A Python-based automation script that uses Amazon Bedrock AgentCore Browser to interact with the deployed Chat_Application, capture screenshots, and collect test reports.
- **Evidence_Artifacts**: The set of screenshots, test reports, and metadata files produced by the Evidence_Agent during a pipeline run.
- **Artifact_Store**: An Amazon S3 bucket used to persist Evidence_Artifacts with organized prefixes per pipeline run.
- **Terraform_Configuration**: A set of HashiCorp Terraform files that define and provision all required AWS infrastructure for the Chat_Application and Artifact_Store.
- **Libre_Chat**: Libre.Chat — the open-source chat application framework used to build the Chat_Application.
- **AgentCore_Browser**: Amazon Bedrock AgentCore Browser — a managed, containerized Chrome browser environment that enables programmatic web interaction, navigation, and screenshot capture.
- **Bedrock_Models**: Amazon Bedrock foundation models — managed large language models (LLMs) accessed via the Amazon Bedrock API, used as the AI/LLM backend for the Chat_Application. Models are accessed via cross-region (global) inference, which routes requests to model endpoints in other regions using inference profile ARNs or region-prefixed model IDs (e.g., `us.anthropic.claude-3-5-sonnet-20241022-v2:0`).

## Requirements

### Requirement 1: Chat Application Deployment

**User Story:** As a developer, I want a simple chat application deployed on AWS, so that I have a working target application to demonstrate the evidence pipeline against.

#### Acceptance Criteria

1. THE Chat_Application SHALL provide a web-based messaging interface accessible over HTTPS on a public URL.
2. THE Chat_Application SHALL support sending and displaying text messages between at least two users in a shared channel.
3. THE Chat_Application SHALL be built using Libre.Chat as the chat application framework, requiring no custom messaging protocol implementation. The Chat_Application source code SHALL be maintained as a fork of the upstream danny-avila/LibreChat repository, enabling future customisation while preserving the ability to merge upstream updates. The CI/CD pipeline SHALL build the Docker image from the forked source using LibreChat's own Dockerfile.
4. WHEN the Chat_Application is deployed, THE Chat_Application SHALL be reachable and return an HTTP 200 status on its health-check endpoint within 120 seconds of deployment completion.
5. THE Chat_Application SHALL be configured to use Bedrock_Models as its AI/LLM backend, leveraging LibreChat's native Amazon Bedrock endpoint support.

### Requirement 2: AWS Infrastructure via Terraform

**User Story:** As a DevOps engineer, I want all AWS infrastructure defined in Terraform, so that the environment is reproducible, version-controlled, and easy to tear down.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL define all AWS resources required to run the Chat_Application, including compute, networking, and storage resources.
2. THE Terraform_Configuration SHALL define the Artifact_Store as an S3 bucket with a unique, configurable name.
3. THE Terraform_Configuration SHALL be executable with `terraform apply` from a clean state without manual pre-configuration beyond AWS credentials and a Terraform backend.
4. WHEN `terraform destroy` is executed, THE Terraform_Configuration SHALL remove all provisioned resources without leaving orphaned infrastructure.
5. THE Terraform_Configuration SHALL use parameterized variables for configurable values such as AWS region, instance size, and S3 bucket name, targeting a single dev environment.
6. THE Terraform_Configuration SHALL provision IAM permissions on the ECS task role to allow invoking Bedrock_Models (e.g., `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`) so that the Chat_Application can access Bedrock as its AI/LLM backend.

### Requirement 3: GitHub Actions CI/CD Pipeline

**User Story:** As a developer, I want a GitHub Actions pipeline that triggers on merge to the main branch, so that every merged change is automatically built, tested, deployed, and evidence-collected.

#### Acceptance Criteria

1. WHEN a pull request is merged into the main branch, THE Pipeline SHALL trigger automatically.
2. THE Pipeline SHALL include a build stage that compiles or packages the Chat_Application.
3. THE Pipeline SHALL include a test stage that runs the application's unit and integration test suites and produces a test report in a standard format (JUnit XML or equivalent).
4. THE Pipeline SHALL include a deploy stage that provisions or updates the AWS infrastructure using the Terraform_Configuration and deploys the Chat_Application.
5. THE Pipeline SHALL include an evidence-collection stage that executes after the deploy stage completes successfully.
6. IF any stage in the Pipeline fails, THEN THE Pipeline SHALL halt execution of subsequent stages and report the failure status in the GitHub Actions UI.
7. THE Pipeline SHALL store AWS credentials and sensitive configuration values as GitHub Actions encrypted secrets, not as plaintext in workflow files.

### Requirement 4: Evidence Collection via AgentCore Browser

**User Story:** As a compliance reviewer, I want the pipeline to automatically capture visual screenshots and test reports of the deployed application, so that I have verifiable evidence of each release without manual effort.

#### Acceptance Criteria

1. WHEN the evidence-collection stage runs, THE Evidence_Agent SHALL launch an AgentCore_Browser session targeting the deployed Chat_Application URL.
2. WHEN the AgentCore_Browser session is active, THE Evidence_Agent SHALL navigate to the Chat_Application login page and capture a full-page screenshot.
3. WHEN the AgentCore_Browser session is active, THE Evidence_Agent SHALL navigate to the main chat interface and capture a full-page screenshot showing the messaging view.
4. THE Evidence_Agent SHALL capture a minimum of two distinct screenshots: one of the login or landing page and one of the active chat interface.
5. THE Evidence_Agent SHALL collect the test report generated during the Pipeline test stage and include the test report in the Evidence_Artifacts.
6. IF the AgentCore_Browser session fails to connect to the Chat_Application within 60 seconds, THEN THE Evidence_Agent SHALL log the connection failure, capture a screenshot of the error state, and exit with a non-zero status code.
7. IF screenshot capture fails for any page, THEN THE Evidence_Agent SHALL log the failure reason and continue attempting to capture remaining screenshots before exiting.

### Requirement 5: Evidence Artifact Storage in S3

**User Story:** As a compliance reviewer, I want all evidence artifacts stored in an organized S3 bucket, so that I can retrieve and audit evidence for any specific pipeline run.

#### Acceptance Criteria

1. WHEN the Evidence_Agent completes execution, THE Evidence_Agent SHALL upload all Evidence_Artifacts to the Artifact_Store.
2. THE Evidence_Agent SHALL organize uploaded artifacts under an S3 key prefix that includes the pipeline run identifier and a timestamp in ISO 8601 format (e.g., `evidence/{run_id}/{timestamp}/`).
3. THE Evidence_Agent SHALL upload screenshots in PNG or JPEG format.
4. THE Evidence_Agent SHALL upload the test report in its original format (JUnit XML or equivalent).
5. THE Evidence_Agent SHALL generate and upload a JSON manifest file listing all uploaded artifacts, their S3 keys, capture timestamps, and file sizes.
6. IF the upload to the Artifact_Store fails, THEN THE Evidence_Agent SHALL retry the upload up to 3 times with exponential backoff before reporting the failure.

### Requirement 6: Pipeline Observability and Reporting

**User Story:** As a developer, I want clear visibility into the pipeline execution and evidence collection results, so that I can quickly identify issues and verify successful runs.

#### Acceptance Criteria

1. WHEN the Pipeline completes successfully, THE Pipeline SHALL output a summary in the GitHub Actions job log that includes the S3 URI of the uploaded Evidence_Artifacts.
2. WHEN the evidence-collection stage completes, THE Evidence_Agent SHALL log the count of screenshots captured and the count of test reports collected.
3. IF any evidence-collection step fails, THEN THE Evidence_Agent SHALL include the failure details in the GitHub Actions job log with sufficient context to diagnose the issue.
