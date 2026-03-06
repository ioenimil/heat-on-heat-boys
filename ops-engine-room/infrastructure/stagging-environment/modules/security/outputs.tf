output "app_runner_connector_sg_id" { value = aws_security_group.app_runner_connector.id }
output "airflow_ec2_sg_id" { value = aws_security_group.airflow_ec2.id }
output "rds_sg_id" { value = aws_security_group.rds.id }
