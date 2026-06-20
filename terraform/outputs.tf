output "api_url" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "cloudfront_url" {
  description = "CloudFront distribution URL"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "lambda_function_name" {
  value = aws_lambda_function.main.function_name
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.main.name
}

output "frontend_bucket" {
  value = aws_s3_bucket.frontend.bucket
}
