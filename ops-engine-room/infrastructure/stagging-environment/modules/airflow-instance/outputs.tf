output "instance_id" {
  description = "The ID of the Airflow EC2 instance"
  value       = aws_instance.airflow.id
}

output "public_ip" {
  description = "The public IP of the Airflow EC2 instance"
  value       = aws_instance.airflow.public_ip
}

output "private_ip" {
  description = "The private IP of the Airflow EC2 instance"
  value       = aws_instance.airflow.private_ip
}
