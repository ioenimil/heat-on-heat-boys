resource "aws_db_subnet_group" "main" {
  name       = "servicehub-db-subnet-group"
  subnet_ids = var.private_subnet_ids
}

resource "random_password" "db_password" {
  length  = 16
  special = false
}

resource "aws_secretsmanager_secret" "rds_credentials" {
  name                    = "servicehub-rds-credentials-${random_password.db_password.result}"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "rds_credentials" {
  secret_id     = aws_secretsmanager_secret.rds_credentials.id
  secret_string = jsonencode({ username = "postgres", password = random_password.db_password.result })
}

resource "aws_db_instance" "main" {
  identifier             = "servicehub-db"
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t3.micro"
  username               = "postgres"
  password               = random_password.db_password.result
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.rds_sg_id]
  skip_final_snapshot    = true
}
