# Environment Config README

This document outlines the required secrets and environment variables needed to successfully run the CI/CD pipelines and deploy the application.

## 1. GitHub Actions Secrets
These secrets must be added to your GitHub repository (Settings -> Secrets and variables -> Actions).

| Secret Name | Purpose | Example / Notes |
| :--- | :--- | :--- |
| `AWS_ROLE_ARN` | The ARN of the IAM Role for GitHub Actions (OIDC) to assume for pushing to ECR. | `arn:aws:iam::123456789012:role/GitHubActionsECRRole` |
| `AWS_REGION` | The AWS region where your infrastructure is deployed. | `eu-west-1` |
| `ECR_REPOSITORY` | The name of your ECR repository. | `servicehub-app` |
| `EC2_HOST` | The public IP or DNS of the Airflow EC2 instance. | `18.201.251.31` (Get from terraform output `airflow_ec2_public_ip`) |
| `EC2_USER` | The SSH username for the Airflow EC2 instance. | `ubuntu` |
| `EC2_SSH_KEY` | The private SSH key used to connect to the Airflow instance. | Contents of your `.pem` or `.key` file |
| `DB_HOST` | The RDS instance endpoint. | `servicehub-db...rds.amazonaws.com` |
| `DB_PORT` | The RDS instance port. | `5432` |
| `DB_NAME` | The database name. | `servicehub` |
| `DB_USER` | The database master username. | `postgres` |
| `DB_PASSWORD` | The database master password. | `supersecretpassword` |

## 2. App Runner Environment Variables
When the application container runs in AWS App Runner, it will need environment variables to connect to the provisioned infrastructure (like the RDS database).

**Note:** Currently, the `modules/app/main.tf` configuration does not explicitly pass environment variables to App Runner. If your application code requires them, you will need to add them to the `aws_apprunner_service.main` resource under `source_configuration.image_repository.image_configuration.runtime_environment_variables`.

### Recommended App Variables:
If your backend connects to the database, you likely need to provide the database credentials to the App Runner service:

| Variable Name | Purpose | Example |
| :--- | :--- | :--- |
| `DB_HOST` | RDS instance endpoint | `servicehub-db...rds.amazonaws.com` |
| `DB_PORT` | RDS instance port | `5432` |
| `DB_NAME` | Database name | `servicehub` |
| `DB_USER` | Database username | `postgres` |
| `DB_PASSWORD` | Database password | `supersecretpassword` |
| `PORT` | The port the application listens on | `8080` (Must match App Runner config) |
