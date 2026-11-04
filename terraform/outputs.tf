output "function_name" {
  value = aws_lambda_function.review.function_name
}

output "topic_arn" {
  value = aws_sns_topic.alerts.arn
}

output "schedule" {
  value = aws_cloudwatch_event_rule.weekly.schedule_expression
}
