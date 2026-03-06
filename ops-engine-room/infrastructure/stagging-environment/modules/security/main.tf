# App Runner VPC Connector SG
resource "aws_security_group" "app_runner_connector" {
  name        = "app-runner-connector-sg"
  description = "Security group for App Runner VPC Connector"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr_block]
  }
}

# MWAA SG
resource "aws_security_group" "mwaa" {
  name        = "mwaa-sg"
  description = "Security group for MWAA"
  vpc_id      = var.vpc_id

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# RDS SG
resource "aws_security_group" "rds" {
  name        = "rds-sg"
  description = "Security group for RDS instance"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_runner_connector.id, aws_security_group.mwaa.id]
  }
}
