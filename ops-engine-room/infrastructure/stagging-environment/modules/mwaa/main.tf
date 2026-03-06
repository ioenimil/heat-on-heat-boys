resource "aws_iam_role" "mwaa_execution_role" {
  name = "mwaa-execution-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{ Action = "sts:AssumeRole", Principal = { Service = ["airflow.amazonaws.com", "airflow-env.amazonaws.com"] }, Effect = "Allow" }]
  })
}

resource "aws_iam_role_policy" "mwaa_execution_policy" {
  name = "mwaa-execution-policy"
  role = aws_iam_role.mwaa_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      { Effect = "Allow", Action = "airflow:PublishMetrics", Resource = "*" },
      { Effect = "Allow", Action = "s3:ListAllMyBuckets", Resource = "*" },
      { Effect = "Allow", Action = ["s3:GetObject*", "s3:GetBucket*", "s3:List*"], Resource = [var.mwaa_bucket_arn, "${var.mwaa_bucket_arn}/*"] },
      { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:CreateLogGroup", "logs:PutLogEvents", "logs:GetLogEvents", "logs:GetLogRecord", "logs:GetLogGroupFields", "logs:GetQueryResults", "logs:DescribeLogGroups"], Resource = "arn:aws:logs:*:*:log-group:airflow-*" },
      { Effect = "Allow", Action = ["cloudwatch:PutMetricData"], Resource = "*" }
    ]
  })
}

resource "aws_mwaa_environment" "main" {
  name               = "servicehub-mwaa"
  airflow_version    = "2.8.1"
  execution_role_arn = aws_iam_role.mwaa_execution_role.arn
  source_bucket_arn  = var.mwaa_bucket_arn
  dag_s3_path        = "dags/"

  network_configuration {
    security_group_ids = [var.mwaa_sg_id]
    subnet_ids         = var.private_subnet_ids
  }
}
