# Implementation Plan: Evidence Pipeline Chat App

## Overview

This plan implements a single dev-environment CI/CD evidence collection pipeline. A LibreChat instance is deployed to AWS via Terraform, a GitHub Actions pipeline automates build/test/deploy/evidence-collection on merge to main, and a Python Evidence Agent uses Amazon Bedrock AgentCore Browser to capture screenshots and test reports, storing them in S3.

Tasks are ordered so that foundational infrastructure comes first, followed by the application layer, then the Evidence Agent, then the pipeline workflow, and finally integration wiring.

## Tasks

- [x] 1. Set up Terraform project structure and root configuration
  - Create `terraform/` directory with `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf`
  - Define provider configuration for AWS with `aws_region` variable (default `ap-southeast-1`)
  - Define parameterized variables: `aws_region`, `instance_size`, `s3_bucket_name`, `project_name`
  - Tag all resources with `environment = "dev"` hardcoded
  - _Requirements: 2.1, 2.3, 2.5_

- [x] 2. Implement Terraform networking module
  - [x] 2.1 Create `terraform/modules/networking/` with `main.tf`, `variables.tf`, `outputs.tf`
    - Define VPC, public subnets (for ALB), private subnets (for ECS), internet gateway, NAT gateway, route tables, and security groups
    - Output VPC ID, subnet IDs, and security group IDs for use by compute and storage modules
    - _Requirements: 2.1_

  - [x] 2.2 Create `terraform/modules/storage/` with `main.tf`, `variables.tf`, `outputs.tf`
    - Define S3 evidence bucket with configurable name via `s3_bucket_name` variable
    - Define EFS file system for MongoDB persistence
    - Output bucket name, bucket ARN, and EFS file system ID
    - _Requirements: 2.1, 2.2_

- [x] 3. Implement Terraform compute module
  - [x] 3.1 Create `terraform/modules/compute/` with `main.tf`, `variables.tf`, `outputs.tf`
    - Define ECS cluster, task definition (LibreChat + MongoDB sidecar), ECS service, ALB with HTTPS listener, ACM certificate, and IAM roles (task execution role, task role with S3 write access and Bedrock invoke permissions)
    - Map `instance_size` variable to Fargate CPU/memory settings
    - Configure LibreChat container on port 3080 with health check on `GET /api/health`
    - Configure MongoDB sidecar with EFS mount for data persistence
    - Attach IAM policy to ECS task role granting `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` permissions, with resource ARNs covering cross-region inference profiles (e.g., `arn:aws:bedrock:*::foundation-model/*` and `arn:aws:bedrock:*:*:inference-profile/*`)
    - Output ALB URL and ECS service name
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 2.1, 2.6_

  - [x] 3.2 Wire all modules together in root `main.tf`
    - Connect networking outputs to compute and storage module inputs
    - Define root-level outputs: ALB URL, S3 bucket name
    - Ensure `terraform apply` works from clean state and `terraform destroy` removes all resources
    - _Requirements: 2.3, 2.4_

  - [ ]* 3.3 Validate Terraform configuration
    - Run `terraform validate` to check syntax and configuration correctness
    - Run `terraform plan` to verify resource creation without errors
    - _Requirements: 2.3_

- [x] 4. Checkpoint - Verify Terraform configuration
  - Ensure all Terraform modules are wired correctly and `terraform validate` passes, ask the user if questions arise.

- [x] 5. Configure LibreChat with Amazon Bedrock models
  - [x] 5.1 Create `librechat.yaml` configuration file
    - Define Bedrock endpoint with `enabled: true`
    - Configure `availableRegions` with `ap-southeast-1`
    - Specify default models using cross-region inference IDs (e.g., `us.anthropic.claude-3-5-sonnet-20241022-v2:0`, `us.amazon.nova-micro-v1:0`)
    - Set `titleModel` and `summaryModel` to a cross-region Bedrock model ID
    - _Requirements: 1.5_

  - [x] 5.2 Update Terraform ECS task definition for Bedrock configuration
    - Mount `librechat.yaml` into the LibreChat container (via EFS or baked into image)
    - Add `AWS_DEFAULT_REGION` environment variable (set to `ap-southeast-1`) to the LibreChat container definition
    - Ensure the ECS task role IAM policy includes `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` permissions, scoped to allow cross-region inference profile ARNs
    - _Requirements: 1.5, 2.6_

- [x] 6. Checkpoint - Verify Terraform and Bedrock configuration
  - Ensure all Terraform modules are wired correctly and `terraform validate` passes, ask the user if questions arise.

- [x] 7. Implement Evidence Agent configuration and data models
  - [x] 7.1 Create `evidence_agent/` directory with `config.py`
    - Implement `PipelineConfig` dataclass sourced from environment variables (`app_url`, `s3_bucket`, `run_id`, `aws_region`, `connection_timeout`, `max_upload_retries`)
    - Implement validation that fails fast with descriptive error messages for missing required variables
    - _Requirements: 4.1, 5.1_

  - [x] 7.2 Create `evidence_agent/artifacts.py` with data models and core functions
    - Implement `ArtifactEntry`, `Manifest`, `ManifestSummary`, `ScreenshotResult` dataclasses
    - Implement `build_s3_key_prefix(run_id, timestamp)` returning `evidence/{run_id}/{iso_timestamp}/`
    - Implement `generate_manifest(artifacts)` producing JSON manifest with artifact entries and summary counts
    - Implement `upload_with_retry(s3_client, bucket, key, body, max_retries=3)` with exponential backoff and jitter
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ]* 7.3 Write property test: S3 key prefix format correctness
    - **Property 2: S3 key prefix format correctness**
    - Use Hypothesis to generate random run IDs (non-empty alphanumeric strings) and random datetimes
    - Assert prefix matches `evidence/{run_id}/{iso_timestamp}/` pattern, timestamp is valid ISO 8601, and prefix ends with `/`
    - Minimum 100 iterations
    - **Validates: Requirements 5.2**

  - [ ]* 7.4 Write property test: Manifest completeness and consistency
    - **Property 3: Manifest completeness and consistency**
    - Use Hypothesis to generate random lists of `ArtifactEntry` with varying types, sizes, and names
    - Assert manifest contains exactly one entry per artifact with matching fields, `summary.total_artifacts` equals list length, and `total_screenshots` + `total_reports` sum correctly by type
    - Minimum 100 iterations
    - **Validates: Requirements 5.5, 6.2**

  - [ ]* 7.5 Write property test: Upload retry with exponential backoff
    - **Property 4: Upload retry with exponential backoff**
    - Use Hypothesis to generate random failure counts (0 to max_retries+1) with a mock S3 client
    - Assert retry count equals `min(failure_count, max_retries)`, delays double from base, success stops retries, exhausted retries raise error
    - Minimum 100 iterations
    - **Validates: Requirements 5.6**

  - [ ]* 7.6 Write property test: Artifact summary counts match actual artifacts
    - **Property 5: Artifact summary counts match actual artifacts**
    - Use Hypothesis to generate random artifact lists with mixed types ("screenshot", "test_report")
    - Assert summary screenshot count equals count of type "screenshot" and report count equals count of type "test_report"
    - Minimum 100 iterations
    - **Validates: Requirements 6.2**

  - [ ]* 7.7 Write unit tests for artifacts module
    - Test `build_s3_key_prefix` with specific known inputs
    - Test `generate_manifest` with empty list, single artifact, and multiple artifacts
    - Test `upload_with_retry` success on first attempt, success on retry, and failure after max retries
    - Test manifest JSON serialization format matches expected schema
    - _Requirements: 5.2, 5.5, 5.6_

- [x] 8. Implement Evidence Agent browser and screenshot modules
  - [x] 8.1 Create `evidence_agent/browser.py`
    - Implement `create_browser_session(app_url, timeout=60)` using `bedrock-agentcore` SDK
    - Handle connection timeout: log failure with URL and timeout duration, capture error-state screenshot if possible, exit with non-zero status
    - _Requirements: 4.1, 4.6_

  - [x] 8.2 Create `evidence_agent/screenshots.py`
    - Implement `capture_page_screenshot(page, page_name)` returning `ScreenshotResult`
    - Implement `capture_all_screenshots(page, pages_config)` that iterates all pages, logs individual failures, and continues to remaining pages without short-circuiting
    - Capture login/landing page and chat interface screenshots as PNG
    - _Requirements: 4.2, 4.3, 4.4, 4.7_

  - [ ]* 8.3 Write property test: Partial screenshot failure resilience
    - **Property 1: Partial screenshot failure resilience**
    - Use Hypothesis to generate random page lists and random failure subsets
    - Mock the page screenshot function to fail for the designated subset
    - Assert all pages are attempted, each failure is logged, and successful screenshots are returned
    - Minimum 100 iterations
    - **Validates: Requirements 4.7**

  - [ ]* 8.4 Write unit tests for browser and screenshots modules
    - Test `create_browser_session` timeout handling with mock AgentCore client
    - Test `capture_page_screenshot` success and failure paths
    - Test `capture_all_screenshots` with all-success, all-failure, and mixed scenarios
    - Test error-state screenshot capture on connection timeout
    - _Requirements: 4.2, 4.3, 4.6, 4.7_

- [x] 9. Implement Evidence Agent main orchestrator
  - [x] 9.1 Create `evidence_agent/main.py`
    - Load configuration from environment variables via `PipelineConfig`
    - Create AgentCore Browser session, capture screenshots, collect test report from test stage
    - Generate JSON manifest listing all artifacts with S3 keys, timestamps, and file sizes
    - Upload all artifacts (screenshots, test report, manifest) to S3 under `evidence/{run_id}/{iso_timestamp}/` prefix
    - Log summary: count of screenshots captured, count of test reports collected, S3 URI of uploaded artifacts
    - Exit with non-zero status on critical failures (connection timeout, all uploads failed)
    - _Requirements: 4.1, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3_

  - [x] 9.2 Create `evidence_agent/requirements.txt`
    - Include `bedrock-agentcore`, `playwright`, `boto3`, `pytest`, `hypothesis`
    - Pin to compatible versions for Python 3.10+
    - _Requirements: 4.1_

- [x] 10. Checkpoint - Verify Evidence Agent
  - Ensure all Evidence Agent unit and property tests pass, ask the user if questions arise.

- [x] 11. Create GitHub Actions pipeline workflow
  - [x] 11.1 Create `.github/workflows/evidence-pipeline.yml` with build and test jobs
    - Define workflow trigger on `push` to `main` branch
    - Implement `build` job: Docker build, push to ECR, lint
    - Implement `test` job (needs `build`): run `pytest`, generate JUnit XML report at `test-results/report.xml`, upload as workflow artifact
    - Use GitHub Actions encrypted secrets for AWS credentials and sensitive config
    - _Requirements: 3.1, 3.2, 3.3, 3.7_

  - [x] 11.2 Add deploy-dev and evidence jobs to the pipeline
    - Implement `deploy-dev` job (needs `test`): run `terraform apply` targeting dev, update ECS service with new task definition, poll health check endpoint for HTTP 200 within 120 seconds
    - Implement `evidence` job (needs `deploy-dev`): run Evidence Agent Python script, output S3 URI of uploaded artifacts in job summary
    - Add failure handling: `if: failure()` steps to annotate failures in Actions UI, halt subsequent stages on failure
    - _Requirements: 3.4, 3.5, 3.6, 6.1, 6.3_

- [x] 12. Wire pipeline outputs and final integration
  - [x] 12.1 Connect pipeline stages to Terraform outputs
    - Pass ALB URL from `deploy-dev` stage to `evidence` stage as environment variable
    - Pass S3 bucket name from Terraform outputs to Evidence Agent config
    - Pass test report artifact from `test` stage to `evidence` stage
    - _Requirements: 3.4, 3.5, 4.5_

  - [x] 12.2 Add pipeline summary and observability outputs
    - Output S3 URI of evidence artifacts in GitHub Actions job log on successful completion
    - Log screenshot count and test report count in evidence job summary
    - Include failure details with diagnostic context in job log on evidence-collection failures
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document using Hypothesis
- Unit tests validate specific examples and edge cases
- The pipeline targets a single dev environment only — no multi-environment setup
