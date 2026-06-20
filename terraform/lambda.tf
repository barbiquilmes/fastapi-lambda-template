resource "aws_lambda_function" "main" {
  function_name    = var.app_name
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  handler          = "main.handler"
  runtime          = "python3.12"
  architectures    = ["x86_64"]
  role             = aws_iam_role.lambda.arn
  timeout          = var.lambda_timeout
}
