# FastAPI Lambda Template — Learnings

What we built and what went wrong. Use this as a recipe to replicate on a future project.

## What We Built

A private web app on AWS with:
- FastAPI backend running on Lambda (Python 3.12, x86_64)
- API Gateway HTTP API routing requests to Lambda
- DynamoDB for data storage
- SSM Parameter Store for secrets (credentials + JWT signing key)
- JWT authentication (username/password → 7-day token)
- Static HTML frontend hosted on S3 + CloudFront
- All infrastructure managed with Terraform

## Files in This Folder

| File | What it covers |
|---|---|
| `01-aws-infrastructure.md` | Architecture overview + full Terraform deployment guide |
| `02-gotchas.md` | Everything that broke and why — read this first next time |
| `03-security.md` | What's protected, what isn't, and why |
| `04-updating-lambda.md` | How to redeploy after changes |
| `05-https-tls-handshake.md` | Deep dive on TLS/HTTPS with step-by-step diagrams |

## Quick Stack Reference

| Layer | Service | Notes |
|---|---|---|
| Frontend | S3 + CloudFront | Single HTML file, private bucket via OAC |
| API routing | API Gateway HTTP API | `$default` route → Lambda, payload format v2.0 |
| Compute | AWS Lambda (Python 3.12, x86_64) | FastAPI wrapped with Mangum |
| Database | DynamoDB | On-demand billing, composite key (userId + datePillar) |
| Secrets | SSM Parameter Store | SecureString, fetched once at cold start |
| Auth | JWT (HS256) | Issued by Lambda, rate limited via slowapi |
| IaC | Terraform | All infrastructure in `terraform/` |
