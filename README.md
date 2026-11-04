# IAM Access Review

Old and unused IAM credentials are a common way attackers get into AWS accounts. This tool runs automatically every week and emails a report of passwords and access keys that haven't been used in 90+ days, keys old enough that they need to be rotated, and console users without MFA.

The whole stack is defined in Terraform and deployed through a GitHub Actions pipeline: every change goes through a pull request, gets planned automatically, and is applied to AWS only when merged.

![Architecture](docs/architecture.png)

## How it works

Every Monday, an EventBridge rule triggers a Lambda function. The function requests the IAM credential report from AWS and checks each user for passwords or access keys that are unused, keys that are old enough to need rotating, and console users without MFA. It then publishes the findings to an SNS topic, which emails the report to anyone subscribed.

## What it checks

- **Stale console passwords:** not used in 90+ days
- **Stale access keys:** active keys not used in 90+ days
- **Key rotation:** active keys older than 90 days, even if they're used every day
- **Missing MFA:** users who can sign in to the console without MFA
- **Ignore list:** accounts that are supposed to look unused (such as break-glass accounts) are skipped

Keys and passwords that have never been used are measured from their creation date, since there's no last-used date.

## Deployment

```
pull request → terraform fmt / validate / plan → review → merge to main → terraform apply → AWS
```

- **Pull requests** run `terraform fmt`, `validate`, and `plan` against the live state, so you can see exactly what will change before merging.
- **Merging to `main`** runs `terraform apply`.
- **Branch protection** blocks direct pushes and force pushes to `main`, and requires the `plan` check to pass before merging.
- Only one Terraform job runs at a time, so two deploys can't collide on the same state.

## Repository layout

```
├── lambda_function.py           # the access-review logic
├── bootstrap/                   # one-time setup: state bucket + deploy user (run locally)
├── terraform/                   # the main stack: Lambda, IAM role, SNS, EventBridge
└── .github/workflows/
    └── terraform.yml            # plan on PR, apply on merge
```

## Deploy it yourself

**Prerequisites:** an AWS account, Terraform 1.10+, the AWS CLI, and a GitHub repo.

1. **Bootstrap (once, from your laptop):**
   ```bash
   cd bootstrap
   terraform init
   terraform apply -var="region=us-east-2"
   ```
   This creates an encrypted, versioned S3 bucket for Terraform state and a scoped IAM user for GitHub Actions. Note the `state_bucket` and `github_user` outputs.

2. **Create an access key** for the `github_user` in the IAM console.

3. **Add GitHub settings** (repo → Settings → Secrets and variables → Actions):

   | Name | Type | Value |
   |---|---|---|
   | `AWS_REGION` | Variable | your region |
   | `TF_STATE_BUCKET` | Variable | the `state_bucket` output |
   | `AWS_ACCESS_KEY_ID` | Secret | the deploy user's key ID |
   | `AWS_SECRET_ACCESS_KEY` | Secret | the deploy user's secret key |
   | `ALERT_EMAIL` | Secret | where the weekly report goes |

4. **Push to `main`.** The pipeline deploys the stack. Confirm the SNS subscription email AWS sends you.

Settings such as the threshold (`stale_days`) and schedule live in `terraform/variables.tf`. Change them through a pull request.

## Security decisions

- **Least-privilege Lambda role:** the function can only read the credential report and publish to one SNS topic. The IAM report actions require `Resource: "*"` because they don't support resource-level permissions, so the SNS permission is scoped to the single topic.
- **Scoped deploy user:** GitHub Actions can only manage resources with this project's name prefix. The user itself is named outside that prefix, so the pipeline can't modify its own permissions.
- **No secrets in state:** the deploy user's access key is created in the console, not in Terraform, so it never lands in the state file.
- **Protected state:** the state bucket is encrypted, versioned, and blocks all public access.
- **Sensitive values hidden:** the alert email is marked `sensitive`, so it doesn't appear in plan output.
- **Short-lived credentials for my own access:** I used `aws login`, which issues credentials that rotate automatically, instead of creating long-term access keys for myself.

## Lessons learned

- **OIDC was blocked by an SCP.** The usual way for GitHub Actions to reach AWS (OIDC federation, no stored keys) was explicitly denied by the organization's service control policy, so I fell back to a tightly scoped IAM user.
- **Region mismatch.** My CLI couldn't find the function's logs because it was pointed at a different region; the SCP denied Lambda outside the allowed region. Setting the CLI's default region fixed it.
- **Undeployed code.** The first scheduled run took 2 ms and printed nothing. The logs showed the default template was running because I'd never clicked Deploy.
- **`BucketAlreadyOwnedByYou`.** A failed first apply created the state bucket but lost track of it. I used `terraform import` to bring it under Terraform's control instead of recreating it.
- **Workflow push rejected.** Pushing the workflow file needed the `workflow` scope on my GitHub token, which GitHub requires so a leaked token can't add a malicious pipeline.

## Sample alert

![Sample email](docs/sample-email.png)

## What I'd add next

- Switch to OIDC federation if the organization's policy allows it, removing the stored access key
- Automatically deactivate keys after a review period, with an approval step
- Alert when the root account is used
