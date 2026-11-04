variable "region" {
  description = "AWS region your account allows (the one your Lambda runs in)"
  type        = string
}

variable "project" {
  description = "Name prefix for everything this project creates"
  type        = string
  default     = "iam-access-review"
}
