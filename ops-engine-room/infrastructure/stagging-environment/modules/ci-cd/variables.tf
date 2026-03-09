variable "github_repo" {
  description = "GitHub repository name (organization/repository) allowed to assume the role"
  type        = string
}

variable "ecr_repository_arn" {
  description = "ARN of the ECR repository to which GitHub Actions can push images"
  type        = string
}

variable "github_repo" {
  description = "Github repository for the project"
  type = string
}