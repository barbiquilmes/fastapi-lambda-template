resource "aws_dynamodb_table" "main" {
  name         = "${var.app_name}-items"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "datePillar"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "datePillar"
    type = "S"
  }
}
