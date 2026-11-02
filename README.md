# IAM Access Review

Old or  unused IAM credentials are a common way attackers get into AWS accounts. This tool runs automatically every week and emails a report of passwords and access keys that haven’t been used in 90+ days, keys old enough that they need to be rotated, and console users without MFA

![Architecture](docs/architecture.png)

## How it works

Every Monday, an EventBridge rule triggers a Lambda function. The function requests the IAM credential report from AWS and checks each user for passwords or access keys that are unused, keys that are old enough to need rotating, and console users without MFA. It then publishes the findings to an SNS topic, which emails the report to anyone subscribed.

## What it checks

- [Stale passwords and access keys]
- [Console users without MFA]
- [Keys that need to be rotated (older than 90 days)]
- [Users to ignore (root)]

## Security decisions

- **Least privilege:** the Lambda role can only read the credential report
  and publish to one SNS topic. The IAM report actions require `Resource: "*"`
  because they don't support resource-level permissions, so the SNS
  permission is scoped to the single topic.
- **No long-term keys for my own access:** I used `aws login`, which issues
  short-lived credentials that rotate automatically, instead of creating
  access keys for myself.

## Lessons learned

- **Region mismatch:** my CLI couldn't find the function's logs because it
  was pointed at a different region. The account's service control policy
  explicitly denied Lambda outside the allowed region. Setting the CLI's
  default region fixed it.
- **Undeployed code:** the first scheduled run took 2 ms and printed nothing.
  The logs showed the default template was running because I'd never clicked
  Deploy.

## Deploy it yourself

1 Create SNS Topic -> Create Subsription Email -> Confirm subscription in your email 
2 Create Lambda function from scratch -> Create new role with basic permissions -> set timeout to 1 min -> set env variables to your topic arn and days to 0 for testing 
3 Give least permissions it needs with JSON policy 
4 Add Eventbridge trigger and schedule 

## Sample alert

![Sample email](docs/sample-email.png)

## What I'd add next

[1–2 ideas, e.g. rebuild in Terraform, auto-disable keys after review.]
