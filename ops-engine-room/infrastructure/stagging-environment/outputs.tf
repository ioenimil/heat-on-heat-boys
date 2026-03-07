output "airflow_ec2_public_ip" {
  description = "Public IP of the Airflow EC2 instance"
  value       = module.airflow_instance.public_ip
}

output "app_runner_service_url" {
  description = "URL of the App Runner service"
  value       = module.app.app_runner_service_url
}
