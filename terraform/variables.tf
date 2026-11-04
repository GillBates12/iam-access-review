variable "region" {
  description = "AWS region your account allows"
  type        = string
}

variable "project" {
  description = "Name prefix for everything this stack creates"
  type        = string
  default     = "iam-access-review"
}

variable "alert_email" {
  description = "Email address that receives the weekly report"
  type        = string
  sensitive   = true # keeps it out of plan output and PR comments
}

variable "stale_days" {
  description = "Flag passwords and keys unused for this many days"
  type        = number
  default     = 90
}

variable "schedule" {
  description = "When the review runs (UTC)"
  type        = string
  default     = "cron(0 13 ? * MON *)"
}
