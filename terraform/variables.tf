variable "app_name" {
  description = "Application name — used as prefix for all resources"
  type        = string
  default     = "yourapp"
}

variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

variable "lambda_zip_path" {
  description = "Path to the Lambda deployment zip (build it first with 06-updating-lambda.md)"
  type        = string
  default     = "../lambda.zip"
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds. Default 30 — SSM cold start calls need headroom beyond the 3s AWS default"
  type        = number
  default     = 30
}

variable "app_username" {
  description = "Login username stored in SSM"
  type        = string
  sensitive   = true
}

variable "app_password" {
  description = "Login password stored in SSM"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "JWT secret key — generate with: openssl rand -hex 32"
  type        = string
  sensitive   = true
}
