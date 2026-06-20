# 06 — How to Update the Lambda Function

Run these commands from the repo root. 

## Steps

```bash
# 1. Rebuild the package with Linux-compatible dependencies
uv pip install \
  --target package/ \
  --python-platform x86_64-unknown-linux-gnu \
  --python-version 3.12 \
  fastapi uvicorn boto3 pyjwt mangum slowapi

# 2. Copy latest app code
cp main.py package/

# 3. Zip everything
cd package && zip -r ../lambda.zip . -q && cd ..

# 4. Deploy to Lambda
aws lambda update-function-code \
  --function-name your-function-name \
  --zip-file fileb://lambda.zip \
  --region eu-west-1
```

Do this every time `main.py` changes or a new dependency is added.
