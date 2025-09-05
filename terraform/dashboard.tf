resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-main-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric",
        x      = 0,
        y      = 0,
        width  = 12,
        height = 6,
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "HealthyHostCount", "TargetGroup", aws_lb_target_group.app.arn_suffix, "LoadBalancer", aws_lb.main.arn_suffix]
          ],
          period = 300,
          stat   = "Average",
          region = var.aws_region,
          title  = "1. Availability: Healthy Hosts"
        }
      },
      {
        type   = "metric",
        x      = 0,
        y      = 6,
        width  = 12,
        height = 6,
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.main.name, "ClusterName", aws_ecs_cluster.main.name],
            [".", "MemoryUtilization", ".", ".", ".", "."]
          ],
          period = 300,
          stat   = "Average",
          region = var.aws_region,
          title  = "2. Performance: CPU & Memory Utilization"
        }
      },
      {
        type   = "metric",
        x      = 12,
        y      = 0,
        width  = 12,
        height = 6,
        properties = {
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.time_checker.function_name, { "stat": "Sum" }]
          ],
          period = 300,
          stat   = "Sum",
          region = var.aws_region,
          title  = "3. Health Check: Lambda Errors"
        }
      }
    ]
  })
}