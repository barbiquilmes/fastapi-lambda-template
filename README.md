# fastapi-lambda-template

A production-ready template for deploying a **FastAPI** app on **AWS Lambda** with API Gateway, DynamoDB, JWT auth, and a static frontend on S3 + CloudFront. Infrastructure managed with Terraform.

Built and battle-tested while building a personal app. The `learnings/` folder documents everything that went wrong and how to fix it.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Mangum (ASGI adapter for Lambda) |
| Runtime | Python 3.12 on AWS Lambda |
| API | API Gateway HTTP API |
| Database | DynamoDB |
| Secrets | SSM Parameter Store |
| Auth | JWT (HS256) + slowapi rate limiting |
| Frontend | Static HTML on S3 + CloudFront |
| IaC | Terraform |
| Package manager | uv |

## Architecture

```
Browser
  │
  ├── CloudFront (HTTPS) ──► S3 ──► index.html
  │
  └── API Gateway (HTTP API)
        │
        └── Lambda (FastAPI + Mangum)
              ├── POST /login     → SSM (credentials + JWT secret)
              ├── POST /items     → DynamoDB
              ├── GET  /items     → DynamoDB
              └── GET  /healthz
```

## Project structure

```
main.py              # FastAPI app + Lambda handler
pyproject.toml       # Dependencies (uv)
terraform/           # All AWS infrastructure as code
learnings/
  02-aws-infrastructure.md   # Architecture deep dive + deployment steps
  04-gotchas.md
  05-security.md
  06-updating-lambda.md
  07-https-tls-handshake.md
```

## Quick start

### 1. Install dependencies

```bash
uv sync
```

### 2. Run locally

```bash
uv run uvicorn main:app --reload
# API available at http://localhost:8000
```

### 3. Deploy to AWS

See `learnings/02-aws-infrastructure.md` for the full walkthrough. The short version:

```bash
# 1. Update main.py with your app name (SSM paths + DynamoDB table)

# 2. Build the Lambda zip
uv pip install \
  --target package/ \
  --python-platform x86_64-unknown-linux-gnu \
  --python-version 3.12 \
  fastapi uvicorn boto3 pyjwt mangum slowapi
cp main.py package/
cd package && zip -r ../lambda.zip . -q && cd ..

# 3. Deploy infrastructure
cd terraform
cp terraform.tfvars.example terraform.tfvars  # fill in your values
terraform init
terraform apply

# 4. Upload frontend
aws s3 cp index.html s3://$(terraform output -raw frontend_bucket)/
```

### Tear down

```bash
cd terraform && terraform destroy
```

## Security features

- JWT authentication on all protected endpoints
- Rate limiting on `/login` (5 attempts/minute per IP via slowapi)
- `/docs` and `/redoc` disabled in production
- Secrets stored in SSM Parameter Store, never in code
- S3 bucket private — CloudFront accesses it via OAC

## Learnings

The `learnings/` folder is the most valuable part of this repo — real issues hit during development:

- `02-aws-infrastructure.md` — architecture explained + full Terraform deployment guide
- `04-gotchas.md` — `/ping` reserved by API Gateway, Mangum config, DynamoDB float issue, and more
- `05-security.md` — what's protected, what isn't, and why
- `07-https-tls-handshake.md` — deep dive on TLS/HTTPS with step-by-step diagrams

## Customization

1. Replace `/yourapp/` in `main.py` with your app name (SSM paths)
2. Replace `yourapp-items` with your DynamoDB table name
3. Set `app_name` to match in `terraform/terraform.tfvars`
4. Replace the example `/items` endpoints with your own
5. Update `aws_region` if not using `eu-west-1`
