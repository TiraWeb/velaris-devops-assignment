# --- SECTION 1: Time Checker Lambda and SNS ---

resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}_lambda_exec_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" } }]
  })
}
resource "aws_iam_role_policy_attachment" "lambda_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
resource "aws_iam_policy" "lambda_custom_policy" {
  name   = "${var.project_name}_lambda_custom_policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      { Action = ["sns:Publish"], Effect = "Allow", Resource = aws_sns_topic.alerts.arn },
      { Action = ["dynamodb:PutItem"], Effect = "Allow", Resource = aws_dynamodb_table.time_validation.arn }
    ]
  })
}
resource "aws_iam_role_policy_attachment" "lambda_custom_attachment" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_custom_policy.arn
}
resource "aws_sns_topic" "alerts" { name = "${var.project_name}-alerts" }
resource "aws_sns_topic_subscription" "email_target" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
resource "aws_lambda_function" "time_checker" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-time-checker"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  
  # THIS IS THE FIX: Increase the timeout from 3s to 15s
  timeout          = 15

  environment {
    variables = {
      SNS_TOPIC_ARN  = aws_sns_topic.alerts.arn
      DYNAMODB_TABLE = aws_dynamodb_table.time_validation.name
      ALB_DNS_NAME   = aws_lb.main.dns_name
    }
  }
}
resource "aws_cloudwatch_event_rule" "every_5_minutes" {
  name                = "${var.project_name}-every-5-minutes"
  schedule_expression = "rate(5 minutes)"
}
resource "aws_cloudwatch_event_target" "lambda" {
  rule = aws_cloudwatch_event_rule.every_5_minutes.name
  arn  = aws_lambda_function.time_checker.arn
}
resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.time_checker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_5_minutes.arn
}

# --- SECTION 2: Business Hours Automation ---

resource "aws_iam_role" "business_hours_lambda_role" {
  name = "${var.project_name}-business-hours-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" } }]
  })
}
resource "aws_iam_policy" "ecs_update_policy" {
  name        = "${var.project_name}-ecs-update-policy"
  description = "Allows Lambda to update the ECS service desired count"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{ Action = ["ecs:UpdateService"], Effect = "Allow", Resource = aws_ecs_service.main.id }]
  })
}
resource "aws_iam_role_policy_attachment" "business_hours_lambda_policy" {
  role       = aws_iam_role.business_hours_lambda_role.name
  policy_arn = aws_iam_policy.ecs_update_policy.arn
}
resource "aws_iam_role_policy_attachment" "business_hours_lambda_basic_execution" {
  role       = aws_iam_role.business_hours_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
resource "aws_lambda_function" "business_hours_controller" {
  filename         = data.archive_file.business_hours_lambda_zip.output_path
  function_name    = "${var.project_name}-business-hours-controller"
  role             = aws_iam_role.business_hours_lambda_role.arn
  handler          = "handler.handler" # Corrected handler name
  runtime          = "python3.9"
  source_code_hash = data.archive_file.business_hours_lambda_zip.output_base64sha256 # Corrected typo from sha26
  environment {
    variables = {
      ECS_CLUSTER_NAME = aws_ecs_cluster.main.name
      ECS_SERVICE_NAME = aws_ecs_service.main.name
    }
  }
}
resource "aws_cloudwatch_event_rule" "start_business_hours" {
  name                = "${var.project_name}-start-work"
  schedule_expression = "cron(0 9 * * ? *)" # 9 AM UTC
}
resource "aws_cloudwatch_event_rule" "stop_business_hours" {
  name                = "${var.project_name}-stop-work"
  schedule_expression = "cron(0 18 * * ? *)" # 6 PM UTC
}
resource "aws_cloudwatch_event_target" "start_ecs_service" {
  rule  = aws_cloudwatch_event_rule.start_business_hours.name
  arn   = aws_lambda_function.business_hours_controller.arn
  input = jsonencode({ "desired_count" : 2 })
}
resource "aws_cloudwatch_event_target" "stop_ecs_service" {
  rule  = aws_cloudwatch_event_rule.stop_business_hours.name
  arn   = aws_lambda_function.business_hours_controller.arn
  input = jsonencode({ "desired_count" : 0 })
}
resource "aws_lambda_permission" "allow_cloudwatch_start" {
  statement_id  = "AllowExecutionFromCloudWatchStart"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.business_hours_controller.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.start_business_hours.arn
}
resource "aws_lambda_permission" "allow_cloudwatch_stop" {
  statement_id  = "AllowExecutionFromCloudWatchStop"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.business_hours_controller.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.stop_business_hours.arn
}