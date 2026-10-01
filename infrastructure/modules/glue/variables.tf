variable "project" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "database_name" {
  description = "Glue catalog database name"
  type        = string
  default     = "northstar_dev"
}

variable "s3_bucket_id" {
  description = "S3 bucket ID for data and artifacts"
  type        = string
}

variable "crawler_name" {
  description = "Name of the raw data Glue crawler"
  type        = string
  default     = "northstar-dev-raw-crawler"
}

variable "data_engineer_role_arn" {
  description = "IAM role ARN for DataEngineer / Glue jobs"
  type        = string
}

variable "transform_job_name" {
  description = "Name of the transform Glue job"
  type        = string
  default     = "northstar-dev-transform"
}

variable "glue_network_connection_name" {
  description = "Optional Glue network connection name for VPC"
  type        = string
  default     = null
}

variable "feature_engineer_job_name" {
  description = "Name of the feature engineer Glue job"
  type        = string
  default     = "northstar-dev-feature-engineer"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
