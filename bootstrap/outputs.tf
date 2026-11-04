output "state_bucket" {
  description = "Put this in the GitHub variable TF_STATE_BUCKET"
  value       = aws_s3_bucket.state.bucket
}

output "github_user" {
  description = "Create an access key for this user in the console, then save it as GitHub secrets"
  value       = aws_iam_user.github.name
}
