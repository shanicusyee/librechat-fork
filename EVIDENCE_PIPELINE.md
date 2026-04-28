# Evidence Pipeline Chat App

A CI/CD evidence collection pipeline that deploys a LibreChat application to AWS and automatically captures visual evidence of each release using Amazon Bedrock AgentCore Browser.

## What This Does

On every merge to `main`, a GitHub Actions pipeline:
1. Builds the LibreChat Docker image and pushes to ECR
2. Runs unit tests and generates a JUnit XML report
3. Deploys infrastructure via Terraform and updates the ECS service
4. Launches an AgentCore Browser session to capture screenshots of the live app
5. Uploads all evidence (screenshots, test reports, manifest) to S3

## Architecture

```mermaid
flowchart LR
    DEV(["👤 Developer"]) -->|push| GH["🐙 GitHub"]
    GH -->|trigger| GA["⚙️ GitHub Actions"]

    GA -->|build & push| ECR[("📦 ECR")]
    GA -->|deploy| ECS["🚀 ECS Fargate<br/>LibreChat + MongoDB"]
    GA -->|collect| AGENT["🤖 Evidence Agent"]

    ECR -.->|pull image| ECS
    ECS -->|served via| ALB["⚖️ ALB"]
    ALB -->|HTTPS| CF["☁️ CloudFront"]

    AGENT -->|browser session| ACB["🌐 AgentCore Browser"]
    ACB -->|screenshots| CF
    AGENT -->|upload| S3[("🗄️ S3 Evidence")]

    ECS -->|invoke model| BEDROCK["🧠 Bedrock<br/>Claude / Nova"]

    USER(["👤 Users"]) -->|browse| CF

    style DEV fill:#e1f5ff,stroke:#0288d1
    style USER fill:#e1f5ff,stroke:#0288d1
    style GH fill:#f0f0f0,stroke:#333
    style GA fill:#f0f0f0,stroke:#333
    style ECS fill:#fff4e1,stroke:#ff9800
    style ALB fill:#fff4e1,stroke:#ff9800
    style CF fill:#fff4e1,stroke:#ff9800
    style ECR fill:#fff4e1,stroke:#ff9800
    style S3 fill:#fff4e1,stroke:#ff9800
    style BEDROCK fill:#f3e5f5,stroke:#9c27b0
    style ACB fill:#f3e5f5,stroke:#9c27b0
    style AGENT fill:#e8f5e9,stroke:#4caf50
```

## Pipeline Stages

```mermaid
flowchart LR
    A["📝 Push to main"] --> B["🔨 Build<br/>Docker + ECR push"]
    B --> C["✅ Test<br/>pytest + JUnit XML"]
    C --> D["🚀 Deploy<br/>Terraform + ECS"]
    D --> E["📸 Evidence<br/>Screenshots + S3"]

    style A fill:#e1f5ff,stroke:#0288d1
    style B fill:#fff4e1,stroke:#ff9800
    style C fill:#e8f5e9,stroke:#4caf50
    style D fill:#fff4e1,stroke:#ff9800
    style E fill:#f3e5f5,stroke:#9c27b0
```

## Evidence Collection Flow

```mermaid
flowchart TD
    START(["🚀 Start Evidence Agent"]) --> BS["🌐 Create AgentCore<br/>Browser Session"]
    BS --> LOGIN["📸 Screenshot 1<br/>Login Page"]
    LOGIN --> AUTH["🔐 Login as demo user"]
    AUTH --> CHAT["📸 Screenshot 2<br/>Chat Interface"]
    CHAT --> MODEL["📸 Screenshot 3<br/>Model Selector"]
    MODEL --> CLAUDE["💬 Send message<br/>to Claude 3.5"]
    CLAUDE --> CLAUDE_SS["📸 Screenshot 4<br/>Claude Response"]
    CLAUDE_SS --> NOVA["💬 Send message<br/>to Amazon Nova"]
    NOVA --> NOVA_SS["📸 Screenshot 5<br/>Nova Response"]
    NOVA_SS --> UPLOAD["☁️ Upload to S3<br/>with manifest"]
    UPLOAD --> END(["✅ Complete"])

    style START fill:#e8f5e9,stroke:#4caf50
    style END fill:#e8f5e9,stroke:#4caf50
    style UPLOAD fill:#fff4e1,stroke:#ff9800
    style LOGIN fill:#f3e5f5,stroke:#9c27b0
    style CHAT fill:#f3e5f5,stroke:#9c27b0
    style MODEL fill:#f3e5f5,stroke:#9c27b0
    style CLAUDE_SS fill:#f3e5f5,stroke:#9c27b0
    style NOVA_SS fill:#f3e5f5,stroke:#9c27b0
```

## Components

| Component | Technology | Purpose |
|---|---|---|
| Chat Application | LibreChat (fork) | Web-based chat UI with Bedrock AI backend |
| Infrastructure | Terraform | VPC, ECS Fargate, ALB, CloudFront, S3, IAM |
| CI/CD Pipeline | GitHub Actions | Build, test, deploy, evidence collection |
| Evidence Agent | Python + AgentCore Browser | Automated screenshot capture via Playwright |
| LLM Backend | Amazon Bedrock | Cross-region inference (Claude 3.5 Sonnet, Nova) |
| Artifact Store | S3 | Organized evidence storage with JSON manifests |

## S3 Evidence Structure

```
s3://evidence-pipeline-chat-app-evidence/
└── evidence/
    └── {run_id}/
        └── {timestamp}/
            ├── screenshots/
            │   ├── login-page.png
            │   ├── chat-interface.png
            │   ├── model-selector.png
            │   ├── claude-response.png
            │   └── nova-response.png
            ├── reports/
            │   └── report.xml
            └── manifest.json
```

## Security

- **ALB** restricted to CloudFront IPs + allowed CIDRs via security group rules
- **GitHub Actions** authenticates via OIDC (no long-lived AWS credentials)
- **Pipeline** dynamically adds/removes runner IP from ALB SG during run
- **S3 buckets** have public access blocked
- **Terraform state** bucket has versioning and encryption enabled

## Setup

### 1. Bootstrap AWS Resources
```bash
cd terraform/bootstrap
terraform init
terraform apply
```
Creates: ECR repo, state bucket, evidence bucket, OIDC role.

### 2. Set GitHub Secrets
| Secret | From Bootstrap Output |
|---|---|
| `AWS_ROLE_ARN` | `github_actions_role_arn` |
| `ECR_REPOSITORY_URL` | `ecr_repository_url` |
| `S3_BUCKET_NAME` | `evidence_bucket_name` |
| `TERRAFORM_BACKEND_BUCKET` | `terraform_state_bucket` |

### 3. Push to Main
```bash
git push origin main
```
Pipeline triggers automatically and runs all 4 stages end-to-end.
