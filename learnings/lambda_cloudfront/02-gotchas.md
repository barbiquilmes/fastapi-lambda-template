# 02 — Gotchas (Read This First Next Time)

Things that went wrong, why, and how to fix them.

---

## 1. `/ping` is a reserved path in API Gateway HTTP API

**Symptom:** `curl https://<api>.execute-api.amazonaws.com/ping` returns `Healthy Connection` with no Lambda log.

**Why:** API Gateway HTTP API intercepts `/ping` and `/sping` as built-in health check paths. The request never reaches your Lambda.

**Fix:** Don't use `/ping` as a route name. Use `/healthz` or `/status` instead.

---

## 2. Mangum needs `lifespan="off"`

**Symptom:** Some routes return unexpected responses or the Lambda behaves inconsistently.

**Why:** Mangum's default `lifespan="auto"` tries to manage ASGI lifespan events, which doesn't work well in Lambda's stateless execution model.

**Fix:**
```python
handler = Mangum(app, lifespan="off")
```

---

## 3. Lambda packages must be built for Linux x86_64 AND the correct Python version

**Symptom:** Lambda throws `Runtime.ImportModuleError: No module named 'pydantic_core._pydantic_core'`

**Why:** Two separate issues can cause this:
1. Packages with compiled C extensions (like `pydantic-core`) built on macOS won't run on Amazon Linux
2. Even with the right platform, if the Python version doesn't match the Lambda runtime, the `.so` file is incompatible (e.g. `cpython-310` on a Python 3.12 runtime)

**How to verify:** After installing, check the filename:
```bash
ls package/pydantic_core/*.so
# Must show: _pydantic_core.cpython-312-x86_64-linux-gnu.so
#                                   ^^^            ^^^^^
#                             Python version    Linux platform
```

**Fix:** Always specify both flags — platform AND Python version matching your Lambda runtime:
```bash
uv pip install \
  --target package/ \
  --python-platform x86_64-unknown-linux-gnu \
  --python-version 3.12 \
  <packages>
```

---

## 4. DynamoDB rejects Python floats

**Symptom:** `TypeError: Float types are not supported. Use Decimal types instead`

**Why:** DynamoDB's Python SDK (`boto3`) does not accept Python `float` — you must convert to `Decimal`.

**Fix:**
```python
from decimal import Decimal

def to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))  # str() avoids floating-point precision issues
    if isinstance(obj, dict):
        return {k: to_decimal(v) for k, v in obj.items()}
    return obj
```
Call `to_decimal(body.values)` before writing to DynamoDB.

---

## 5. JWT decode requires explicit algorithm

**Symptom:** No error, but this is a security vulnerability if you skip it.

**Why:** JWTs include the algorithm in their header. If you don't specify which algorithm to accept on decode, an attacker can craft a token with `"alg": "none"` and bypass signature verification.

**Fix:** Always pass `algorithms=["HS256"]` explicitly:
```python
jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
```

---

## 6. `datetime.utcnow()` is deprecated

**Symptom:** `DeprecationWarning: datetime.utcnow() is deprecated`

**Fix:**
```python
# Wrong
datetime.datetime.utcnow()

# Correct
datetime.datetime.now(datetime.timezone.utc)
```

---

## 7. SSM SecureString requires `WithDecryption=True`

**Symptom:** You get the encrypted ciphertext instead of the actual value.

**Fix:**
```python
ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]
```

---

## 8. Multiple issued JWTs are all valid simultaneously

**Behaviour:** Every time you log in, you get a new token. All previously issued tokens remain valid until they expire (7 days). This is expected with stateless JWT — there's no server-side session to invalidate.

**Implication:** If you need to "log out everywhere", you'd need a token blacklist (e.g. store invalidated JTIs in DynamoDB). For a personal app this isn't necessary.

---

## 9. Lambda test event needs `sourceIp`

**Symptom:** `KeyError: sourceIp` when running a test event in the Lambda console.

**Fix:** Add `"sourceIp": "127.0.0.1"` inside `requestContext.http` in your test event JSON.

---

## 10. SSO profile overriding credentials

**Symptom:** AWS CLI commands fail with "SSO session expired" even when you have valid credentials.

**Why:** The `[default]` profile in `~/.aws/config` was pointing to SSO, overriding your static credentials.

**Fix:** Keep `[default]` minimal (just `region`). Use named profiles for SSO:
```ini
[default]
region = eu-west-1

[profile admin]
sso_start_url = https://...
sso_region = us-east-1
sso_account_id = 123456789
sso_role_name = AdministratorAccess
region = eu-west-1
```
Then use `--profile admin` or run `aws sso login --profile admin`.

---

## 11. CloudFront default root object is not set by the wizard

**Symptom:** Opening the CloudFront URL returns an error (XML or 403) instead of your app.

**Why:** The new multi-step CloudFront wizard doesn't have a field for the default root object. It must be set after creation.

**Fix:** After the distribution is created → General tab → **Edit** → set **Default root object** to `index.html` → Save.

---

## 12. Uploading `index.html` to a subfolder breaks the default root object

**Symptom:** CloudFront returns 403/404 even with default root object set.

**Why:** If you upload to `s3://bucket/some-folder/index.html` and set default root object to `index.html`, CloudFront looks for `/index.html` at the bucket root — not in the subfolder.

**Fix:** Upload `index.html` directly to the bucket root: `s3://bucket/index.html`.

---

## 13. CloudFront caches aggressively — changes don't appear immediately

**Symptom:** You re-upload `index.html` to S3 but the browser still shows the old version.

**Why:** CloudFront caches files at edge locations globally. Uploading to S3 doesn't invalidate the cache.

**Fix:** After re-uploading, go to CloudFront → **Invalidations → Create invalidation** → path `/*` → Create. Wait ~30 seconds.

---

## 15. Default Lambda timeout (3s) is too low for production

**Symptom:** Requests silently time out under load or during slow cold starts.

**Why:** Lambda's default timeout is 3 seconds. Module-level SSM calls at cold start (3 × ~200ms each) plus request processing can eat into this quickly, especially if SSM is slow or the Lambda is under-provisioned.

**Note:** A timeout issue shows as a 504 from API Gateway, not a 500. A 500 with `Runtime.ImportModuleError` is a packaging problem (see gotcha #3), not a timeout.

**Fix:** Set a higher timeout in `terraform/lambda.tf` — costs nothing extra since billing is per ms of actual execution:
```hcl
resource "aws_lambda_function" "main" {
  ...
  timeout = 30
}
```

---

## 16. Always read the relevant AWS skill before debugging

**Lesson learned:** We spent significant time debugging the `/ping` "Healthy Connection" issue manually. The answer was in **Critical Pitfall #3** of the `aws-serverless:api-gateway` skill:

> `/ping` and `/sping` are reserved paths. Do not use for API resources.

**What are AWS skills?** Skills are reference guides for Claude Code (Anthropic's AI coding assistant). They document critical pitfalls and proven patterns for specific services. If you use Claude Code, loading the relevant skill before working on an AWS service can save hours of debugging.

**How to get them:** Install the official plugins in Claude Code:
- `aws-serverless` plugin → Lambda, API Gateway, SAM/CDK skills
- `deploy-on-aws` plugin → IaC, CDK, CloudFormation skills

**Rule for next time:** Before debugging any AWS service issue, invoke the relevant skill:
- API Gateway issues → `aws-serverless:api-gateway`
- Lambda issues → `aws-serverless:aws-lambda`
- Deployment → `aws-serverless:aws-serverless-deployment`
