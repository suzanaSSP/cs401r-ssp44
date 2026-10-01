# 1. Glue Catalog Database
resource "aws_glue_catalog_database" "northstar_dev" {
  name = var.database_name # "northstar_dev"
}

# 2. Upload the ETL Python script to S3
resource "aws_s3_object" "transform_script" {
  bucket = var.s3_bucket_id
  key    = "artifacts/glue/transform.py"
  source = "${path.module}/../../../cs401r-lab2-template/glue-scripts/transform.py"
  etag   = filemd5("${path.module}/../../../cs401r-lab2-template/glue-scripts/transform.py")
}

# 3. Glue Crawler (scans raw CSVs and populates catalog)
resource "aws_glue_crawler" "raw_crawler" {
  name          = var.crawler_name # "northstar-dev-raw-crawler"
  database_name = aws_glue_catalog_database.northstar_dev.name
  role          = var.data_engineer_role_arn

  s3_target {
    path = "s3://${var.s3_bucket_id}/raw/customers/"
  }
}

# 4. Glue ETL Job
resource "aws_glue_job" "transform_job" {
  name         = var.transform_job_name # "northstar-dev-transform"
  role_arn     = var.data_engineer_role_arn
  glue_version = "4.0"

  command {
    name            = "glueetl"
    script_location = "s3://${var.s3_bucket_id}/${aws_s3_object.transform_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--database_name" = aws_glue_catalog_database.northstar_dev.name
    "--table_name"    = "customers"
    "--output_path"   = "s3://${var.s3_bucket_id}/processed/customers/"
  }

  # Connections / VPC networking if configuring private subnet execution
  connections = var.glue_network_connection_name != null && var.glue_network_connection_name != "" ? [var.glue_network_connection_name] : []
}

# 5. Upload the Feature Engineering Python script to S3
resource "aws_s3_object" "feature_engineer_script" {
  bucket = var.s3_bucket_id
  key    = "artifacts/glue/feature_engineer.py"
  source = "${path.module}/../../../cs401r-lab2-template/glue-scripts/feature_engineer.py"
  etag   = filemd5("${path.module}/../../../cs401r-lab2-template/glue-scripts/feature_engineer.py")
}

# 6. Glue Feature Engineering Job
resource "aws_glue_job" "feature_engineer_job" {
  name         = var.feature_engineer_job_name # "northstar-dev-feature-engineer"
  role_arn     = var.data_engineer_role_arn
  glue_version = "4.0"

  command {
    name            = "glueetl"
    script_location = "s3://${var.s3_bucket_id}/${aws_s3_object.feature_engineer_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--input_path"         = "s3://${var.s3_bucket_id}/processed/customers/"
    "--output_path"        = "s3://${var.s3_bucket_id}/features/customers/"
    "--feature_group_name" = "${var.project}-${var.environment}-customer-features"
    "--region"             = var.aws_region
  }

  connections = var.glue_network_connection_name != null && var.glue_network_connection_name != "" ? [var.glue_network_connection_name] : []
}

