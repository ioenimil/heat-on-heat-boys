resource "aws_ecr_repository" "app" {
  name                 = "servicehub-app"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

data "aws_region" "current" {}

resource "null_resource" "push_dummy_image" {
  depends_on = [aws_ecr_repository.app]

  triggers = {
    repository_url = aws_ecr_repository.app.repository_url
  }

  provisioner "local-exec" {
    command = <<EOF
#!/bin/bash
IMAGE_COUNT=$(aws ecr describe-images --repository-name ${aws_ecr_repository.app.name} --region ${data.aws_region.current.name} --query 'length(imageDetails)' --output text 2>/dev/null || echo "0")

if [ "$IMAGE_COUNT" -gt 0 ]; then
  echo "Images already exist in ECR. Skipping placeholder deployment."
  exit 0
fi

aws ecr get-login-password --region ${data.aws_region.current.name} | docker login --username AWS --password-stdin ${aws_ecr_repository.app.repository_url}
cat <<DUMMY > Dockerfile.dummy
FROM nginx:alpine
RUN sed -i 's/listen  *80;/listen 8080;/' /etc/nginx/conf.d/default.conf
EXPOSE 8080
DUMMY
docker build -t ${aws_ecr_repository.app.repository_url}:latest -f Dockerfile.dummy .
docker push ${aws_ecr_repository.app.repository_url}:latest
EOF
  }
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
  depends_on   = [null_resource.push_dummy_image]
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
