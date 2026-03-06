terraform {
  backend "s3" {
    bucket         = "servicehub-terraform-state-staging"
    key            = "staging/terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true
    dynamodb_table = "servicehub-terraform-locks-staging"
  }
}
