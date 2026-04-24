provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      environment  = "dev"
      project_name = var.project_name
    }
  }
}

# --- Networking ---

module "networking" {
  source       = "./modules/networking"
  project_name = var.project_name
}

# --- Storage ---

module "storage" {
  source             = "./modules/storage"
  project_name       = var.project_name
  s3_bucket_name     = var.s3_bucket_name
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  vpc_cidr           = module.networking.vpc_cidr
}

# --- Compute ---

module "compute" {
  source                = "./modules/compute"
  vpc_id                = module.networking.vpc_id
  public_subnet_ids     = module.networking.public_subnet_ids
  private_subnet_ids    = module.networking.private_subnet_ids
  alb_security_group_id = module.networking.alb_security_group_id
  ecs_security_group_id = module.networking.ecs_security_group_id
  efs_file_system_id    = module.storage.efs_file_system_id
  s3_bucket_arn         = module.storage.s3_bucket_arn
  project_name          = var.project_name
  instance_size         = var.instance_size
}
