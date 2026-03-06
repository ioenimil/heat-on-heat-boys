resource "aws_ecr_repository" "app" {
  name                 = "servicehub-app"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_apprunner_vpc_connector" "connector" {
  vpc_connector_name = "servicehub-vpc-connector"
  subnets            = var.private_subnet_ids
  security_groups    = [var.app_runner_connector_sg_id]
}

resource "aws_iam_role" "apprunner_build_role" {
  name = "AppRunnerBuildRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Principal = { Service = "build.apprunner.amazonaws.com" },
      Effect    = "Allow"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr" {
  role       = aws_iam_role.apprunner_build_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_apprunner_service" "main" {
  service_name = "servicehub-app-runner"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_build_role.arn
    }
    image_repository {
      image_identifier      = "${aws_ecr_repository.app.repository_url}:latest"
      image_repository_type = "ECR"
      # Using a placeholder requirement until pipeline builds actual image
      image_configuration {
        port = "8080"
      }
    }
  }

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.connector.arn
    }
  }

  tags = {
    Name = "servicehub-app-runner"
  }
}
