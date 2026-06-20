---
name: fastapi-lambda
description: Use when deploying FastAPI to AWS Lambda, packaging Python dependencies for Lambda, or building a FastAPI + DynamoDB + JWT auth stack. Covers non-obvious pitfalls not found in general AWS docs.
---

# FastAPI on AWS Lambda

## Before Starting

Always invoke these skills first — they document critical AWS pitfalls:
- API Gateway → `aws-serverless:api-gateway`
- Lambda → `aws-serverless:aws-lambda`
- Deployment → `aws-serverless:aws-serverless-deployment`

## Critical: Packaging Python for Lambda

Must specify BOTH flags — platform AND Python version matching the Lambda runtime:

```bash
uv pip install \
  --target package/ \
  --python-platform x86_64-unknown-linux-gnu \
  --python-version 3.12 \
  <packages>
```

**Verify before zipping:**
```bash
ls package/pydantic_core/*.so
# Must show: _pydantic_core.cpython-312-x86_64-linux-gnu.so
#                                        ^^^            ^^^^^
#                                  Python version   Linux platform
```

If it shows `cpython-310` or `darwin` — wrong. Delete `package/` and reinstall.

## Lambda Timeout

Default is 3 seconds. Module-level SSM calls at cold start (3 × ~200ms) can eat into this under load. Set 30s — costs nothing since billing is per ms of actual execution:

```hcl
resource "aws_lambda_function" "main" {
  timeout = 30
}
```

Note: timeout issues show as **504**, not 500. A 500 with `ImportModuleError` is a packaging problem.

## Mangum

```python
handler = Mangum(app, lifespan="off")  # "off" is required for Lambda
```

## Reserved Paths

Never use `/ping` — API Gateway HTTP API intercepts it and returns `Healthy Connection` without hitting Lambda. Use `/healthz`.

## SSM — Call Outside Route Handlers

```python
# Good — runs once at cold start, cached for all subsequent invocations
JWT_SECRET = get_ssm("/myapp/jwt-secret")

# Bad — calls SSM on every request
@app.get("/items")
def get_items():
    secret = get_ssm("/myapp/jwt-secret")
```

## DynamoDB

Include ALL key attributes in every `put_item` — partition key AND sort key:
```python
table.put_item(Item={
    "userId": "0",       # partition key
    "datePillar": "...", # sort key — missing this throws ValidationException
    "content": "...",
})
```

DynamoDB rejects Python `float` — always use `Decimal(str(value))`.

## Security Defaults

```python
app = FastAPI(docs_url=None, redoc_url=None)        # disable docs in prod
jwt.decode(token, secret, algorithms=["HS256"])      # always explicit algorithm
@limiter.limit("5/minute")                           # rate limit /login
```

## Package Manager

Always `uv`. Never `pip` or `python` directly.
