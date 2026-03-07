module "network" {
  source   = "./modules/network"
  vpc_cidr = var.vpc_cidr
}

module "security" {
  source         = "./modules/security"
  vpc_id         = module.network.vpc_id
  vpc_cidr_block = module.network.vpc_cidr_block
}

module "database" {
  source             = "./modules/database"
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
  rds_sg_id          = module.security.rds_sg_id
}

module "app" {
  source                     = "./modules/app"
  vpc_id                     = module.network.vpc_id
  private_subnet_ids         = module.network.private_subnet_ids
  app_runner_connector_sg_id = module.security.app_runner_connector_sg_id
}

module "airflow_instance" {
  source          = "./modules/airflow-instance"
  vpc_id          = module.network.vpc_id
  subnet_id       = module.network.public_subnet_ids[0]
  airflow_sg_id   = module.security.airflow_ec2_sg_id
  public_key_path = "${path.module}/whoami-service-dev-key.pub"
  instance_type   = "t3.medium"
}

