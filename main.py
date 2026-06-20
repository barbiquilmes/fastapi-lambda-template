import jwt
import datetime
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mangum import Mangum
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ---
# FastAPI + AWS Lambda template
# Stack: FastAPI, Mangum, DynamoDB, SSM Parameter Store, JWT auth, slowapi rate limiting
# Docs disabled in production — enable locally by removing docs_url/redoc_url params
# ---

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(docs_url=None, redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer()

# --- SSM secrets (replace /yourapp/ with your app name) ---

ssm = boto3.client("ssm", region_name="eu-west-1")

def get_ssm(name):
    return ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]

VALID_USERNAME = get_ssm("/templatelog/username")
VALID_PASSWORD = get_ssm("/templatelog/password")
JWT_SECRET     = get_ssm("/templatelog/jwt-secret")

# --- Auth ---

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/login")
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest):
    if body.username != VALID_USERNAME or body.password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = jwt.encode(
        {
            "userId": "0",
            "userName": body.username,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"token": token}

# --- DynamoDB ---

dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
table = dynamodb.Table("templatelog-items")  # replace with your table name


def to_decimal(obj):
    """DynamoDB does not accept Python floats — convert to Decimal."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: to_decimal(v) for k, v in obj.items()}
    return obj

# --- Example protected endpoints ---

class ItemRequest(BaseModel):
    content: str


@app.post("/items")
def create_item(body: ItemRequest, _auth=Depends(require_auth)):
    table.put_item(Item={
        "userId": "0",
        "datePillar": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "content": body.content,
    })
    return {"saved": True}


@app.get("/items")
def get_items(_auth=Depends(require_auth)):
    result = table.query(
        KeyConditionExpression=Key("userId").eq("0")
    )
    return {"items": result["Items"]}


@app.get("/healthz")
def healthz():
    # Note: do NOT use /ping — it is reserved by API Gateway HTTP API
    return {"ok": True}


# --- Lambda handler ---
# Mangum translates Lambda events → ASGI → FastAPI
# lifespan="off" is required for Lambda (stateless execution model)
handler = Mangum(app, lifespan="off")
