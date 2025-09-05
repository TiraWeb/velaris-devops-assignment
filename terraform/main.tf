terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Create a zip file of the Lambda function code to upload
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "../build/lambda_check_package/"
  output_path = "${path.module}/lambda_function.zip"
}

data "archive_file" "business_hours_lambda_zip" {
  type        = "zip"
  source_dir  = "../src/business_hours_lambda/"
  output_path = "${path.module}/business_hours_lambda.zip"
}