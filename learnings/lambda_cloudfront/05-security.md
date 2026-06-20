# 05 — Security

Security concerns for this app and how we addressed them.

---

## Overview

The API (API Gateway + Lambda) is publicly accessible on the internet — anyone with the URL can attempt to call it. This is normal for this architecture. The goal is to make sure only authorised users can read or write data.

---

## Concern 1: API docs exposed publicly

**Problem:** FastAPI auto-generates `/docs` and `/redoc` pages. These were publicly accessible, exposing the full structure of the API to anyone.

**Fix:** Disabled in the `FastAPI()` constructor:
```python
app = FastAPI(docs_url=None, redoc_url=None)
```

---

## Concern 2: Brute-force on /login

**Problem:** `POST /login` was publicly accessible with no limit on attempts. An attacker could try thousands of username/password combinations.

**Fix:** Added rate limiting with `slowapi` — max 5 attempts per minute per IP:
```python
@app.post("/login")
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest):
    ...
```

**Caveat:** This limit is per Lambda instance (in-memory). If AWS scales to multiple instances, each has its own counter. For a personal app this is acceptable.

---

## Concern 3: API not restricted to CloudFront only

**Problem:** The API can be called directly, bypassing CloudFront entirely.

**Why we didn't fix it:** The proper solution requires AWS WAF (~$5/month minimum) plus configuring a shared secret between CloudFront and API Gateway. Too expensive for a personal test app.

**What protects us instead:** JWT auth on all data endpoints + rate limiting on login.

---

## Concern 4: All issued JWTs are valid simultaneously

**Problem:** There is no server-side session. Every login produces a new valid token. Old tokens stay valid until expiry (7 days). You can't "log out everywhere".

**Why we accepted it:** This is standard stateless JWT behaviour. For a personal single-user app, it's fine. A fix would require storing invalidated token IDs in DynamoDB.

---

## What is actually protected

| Endpoint | Protection |
|----------|------------|
| `POST /login` | Rate limited (5/min per IP) |
| `GET /checkins` | Requires valid JWT |
| `POST /checkins` | Requires valid JWT |
| `GET /docs` | Disabled (404) |
| `GET /redoc` | Disabled (404) |

---

## Things worth doing if the app ever becomes more serious

- Store credentials in a proper identity provider (e.g. Cognito) instead of SSM
- Add a token blacklist in DynamoDB to support "log out everywhere"
- Restrict API Gateway to CloudFront only via WAF + shared secret header
- Add CloudWatch alarm on repeated 401s from a single IP
