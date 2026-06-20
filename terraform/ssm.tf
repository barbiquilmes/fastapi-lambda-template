resource "aws_ssm_parameter" "username" {
  name  = "/${var.app_name}/username"
  type  = "SecureString"
  value = var.app_username
}

resource "aws_ssm_parameter" "password" {
  name  = "/${var.app_name}/password"
  type  = "SecureString"
  value = var.app_password
}

resource "aws_ssm_parameter" "jwt_secret" {
  name  = "/${var.app_name}/jwt-secret"
  type  = "SecureString"
  value = var.jwt_secret
}
