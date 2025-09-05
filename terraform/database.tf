resource "aws_dynamodb_table" "time_validation" {
  name           = "${var.project_name}-time-validation"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "container_id"

  attribute {
    name = "container_id"
    type = "S"
  }
}