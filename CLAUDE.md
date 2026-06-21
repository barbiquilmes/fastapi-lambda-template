# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes, merged with project-specific rules for this stack (FastAPI + AWS Lambda + DynamoDB).

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

---

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

---

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

---

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## 5. AWS Skills Rule

**Before ANY work involving an AWS service, invoke the relevant skill first.**

- API Gateway → `aws-serverless:api-gateway`
- Lambda → `aws-serverless:aws-lambda`
- Deployment (SAM/CDK) → `aws-serverless:aws-serverless-deployment`

Do not rely on memory. Read the skill. This rule exists because known issues (like `/ping` being a reserved path) are documented in skill Critical Pitfalls and cost significant debugging time when skipped.

---

## 6. Package Manager

**Always use `uv`. Never `pip` or `python` directly.**

```bash
uv run pytest
uv run uvicorn main:app --reload
uv add <package>
uv pip install --target package/ --python-platform x86_64-unknown-linux-gnu <packages>
```

---

## 7. Lambda-Specific Rules

**Lambda packages must target Linux x86_64.**

Some Python packages contain compiled C extensions (e.g. `pydantic-core`). Always install with the platform flag:

```bash
uv pip install \
  --target package/ \
  --python-platform x86_64-unknown-linux-gnu \
  <packages>
```

**After any change to `main.py` or dependencies, redeploy Lambda:**

```bash
cp main.py package/
cd package && zip -r ../lambda.zip . -q && cd ..
aws lambda update-function-code \
  --function-name your-function \
  --zip-file fileb://lambda.zip \
  --region eu-west-1
```

**Never use `/ping` as a route** — it is reserved by API Gateway HTTP API and will never reach Lambda. Use `/healthz` instead.

**Put SSM calls outside route handlers** — they run once at cold start and are cached in memory for all subsequent invocations:

```python
# Good — runs once at cold start
JWT_SECRET = get_ssm("/yourapp/jwt-secret")

# Bad — calls SSM on every request
@app.get("/items")
def get_items():
    secret = get_ssm("/yourapp/jwt-secret")  # don't do this
```

**Use `lifespan="off"` with Mangum** — Lambda's stateless model doesn't support ASGI lifespan events:

```python
handler = Mangum(app, lifespan="off")
```

---

## 8. Security Rules

- `/docs` and `/redoc` must be disabled in production: `FastAPI(docs_url=None, redoc_url=None)`
- Always specify algorithm explicitly in JWT decode: `algorithms=["HS256"]`
- Secrets live in SSM Parameter Store — never in code or environment variables
- Rate limit `/login` to prevent brute force: `@limiter.limit("5/minute")`
- DynamoDB rejects Python `float` — always convert via `Decimal(str(value))`

---

_Behavioral guidelines adapted from [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)._
