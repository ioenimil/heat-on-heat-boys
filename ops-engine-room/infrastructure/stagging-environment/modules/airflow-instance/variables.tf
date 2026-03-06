variable "vpc_id" {
  description = "The ID of the VPC"
  type        = string
}

variable "subnet_id" {
  description = "The ID of the Subnet where EC2 instance will be deployed"
  type        = string
}

variable "airflow_sg_id" {
  description = "The Security Group ID for the Airflow EC2 instance"
  type        = string
}

variable "public_key_path" {
  description = "Path to the public SSH key"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}
