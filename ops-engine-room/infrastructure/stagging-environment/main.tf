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

module "s3" {
  source = "./modules/s3"
}

module "mwaa" {
  source             = "./modules/mwaa"
  private_subnet_ids = module.network.private_subnet_ids
  mwaa_sg_id         = module.security.mwaa_sg_id
  mwaa_bucket_arn    = module.s3.mwaa_bucket_arn
}
