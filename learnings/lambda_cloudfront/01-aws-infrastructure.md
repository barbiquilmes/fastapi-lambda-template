# 01 — AWS Infrastructure

## Architecture

```
Browser
  │
  ├── CloudFront (HTTPS) ──► S3 ──► index.html
  │
  └── API Gateway (HTTP API)
        │
        └── Lambda (FastAPI + Mangum)
              ├── SSM Parameter Store  ← credentials + JWT secret (cold start)
              └── DynamoDB             ← app data
```

### Why each service

| Service | Role | Why |
|---|---|---|
| **Lambda** | Runs the FastAPI app | No servers to manage, pay per request |
| **API Gateway HTTP API** | Public HTTPS endpoint → Lambda | ~70% cheaper than REST API, all we need is a catch-all route |
| **DynamoDB** | App data | Serverless, on-demand pricing, pairs naturally with Lambda |
| **SSM Parameter Store** | Secrets (credentials, JWT key) | Encrypted at rest, fetched once at cold start and cached |
| **S3** | Hosts static frontend | Cheapest static hosting on AWS |
| **CloudFront** | CDN in front of S3 | Enforces HTTPS, caches at edge, private S3 access via OAC |

### Request flow

1. Browser loads `index.html` from CloudFront → S3
2. `index.html` calls the API Gateway URL directly
3. API Gateway forwards every request to Lambda (`$default` route)
4. Mangum translates the Lambda event into a FastAPI request
5. FastAPI handles routing, auth, and DynamoDB reads/writes
6. Response travels back through the same chain

### Cold start vs warm invocation

On the first Lambda invocation (cold start), the function fetches secrets from SSM and caches them in memory. All subsequent invocations reuse the cached values — SSM is never called again until the next cold start.

---

## Deploying with Terraform

All infrastructure is defined in `terraform/`. One `terraform apply` creates everything.

### Prerequisites

- AWS CLI configured (`aws configure` or SSO)
- Terraform installed (`brew install terraform`)
- Lambda zip built (see step 2 below)

### Step 1 — Choose your app name

Pick a short name (e.g. `myai`). It will be used as a prefix for all AWS resources.

### Step 2 — Update `main.py`

Replace the two placeholder references with your app name:

```python
# SSM paths
JWT_SECRET = get_ssm("/myai/jwt-secret")
USERNAME   = get_ssm("/myai/username")
PASSWORD   = get_ssm("/myai/password")

# DynamoDB table
table = dynamodb.Table("myai-items")
```

### Step 3 — Build the Lambda zip

```bash
uv pip install \
  --target package/ \
  --python-platform x86_64-unknown-linux-gnu \
  --python-version 3.12 \
  fastapi uvicorn boto3 pyjwt mangum slowapi

cp main.py package/
cd package && zip -r ../lambda.zip . -q && cd ..
```

### Step 4 — Fill in `terraform.tfvars`

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
app_name     = "myai"
aws_region   = "eu-west-1"
app_username = "your-username"
app_password = "your-strong-password"
jwt_secret   = ""  # run: openssl rand -hex 32
```

### Step 5 — Deploy

```bash
terraform init
terraform apply
```

Terraform will show a plan of every resource it will create and ask for confirmation.

### Step 6 — Get your URLs

```bash
terraform output
```

```
api_url         = "https://xxxx.execute-api.eu-west-1.amazonaws.com"
cloudfront_url  = "https://xxxx.cloudfront.net"
```

### Step 7 — Upload the frontend

```bash
aws s3 cp index.html s3://$(terraform output -raw frontend_bucket)/
```

### Step 8 — (Optional) Lock down CORS

By default CORS allows all origins (`"*"`). To restrict it to your CloudFront URL, update `main.py`:

```python
allow_origins=["https://xxxx.cloudfront.net"]
```

Then redeploy Lambda:

```bash
cp main.py package/
cd package && zip -r ../lambda.zip . -q && cd ..
aws lambda update-function-code \
  --function-name myai \
  --zip-file fileb://lambda.zip \
  --region eu-west-1
```

---

## Tearing down

```bash
cd terraform
terraform destroy
```

Deletes every resource including SSM secrets. Confirm the plan before proceeding.
