OpenPortfo deployable files

These files package and deploy the app on AWS Academy Learner Lab (us-east-1).
They do not contain AWS credentials.

CloudFormation
  cloudformation.yml        Full template (needs IAM create; may fail in Academy)
  cloudformation-lab.yml    Lab-safe data plane (DynamoDB, S3, Cognito)
  infra-README.md           Parameter notes

Elastic Beanstalk (FastAPI + static UI)
  Procfile
  requirements.txt
  ebextensions/             Copied from backend/.ebextensions
  package-eb.ps1 / .sh      Build the EB source bundle
  deploy-eb.ps1 / .sh       Upload and update the existing environment
  eb-deploy.md              Console / env-var notes (no secrets)

Lambda jobs (news, price, snapshot, email)
  lambda/requirements-lambda.txt
  lambda/README.md
  lambda/package-in-container.sh
  package-lambda.ps1 / .sh
  deploy-lambda.ps1 / .sh   Updates existing function openportfo-jobs
  iam/*.json                Policy documents (no access keys)

Runnable bundles (Assessment 3 deploy folder)
  eb-bundle.zip           Elastic Beanstalk source bundle (FastAPI + Next.js static UI)
  openportfo-jobs.zip     AWS Lambda deployment package for openportfo-jobs

Rebuild from source if needed (from the repo, not from this pack alone):
  .\scripts\package-eb.ps1
  .\scripts\package-lambda.ps1

Set Elastic Beanstalk and Lambda environment properties in the AWS console.
Do not write SMTP_PASSWORD, API keys, or AWS secret keys into these files.
