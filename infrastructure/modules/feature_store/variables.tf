variable "project" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "s3_bucket_id" {
  description = "S3 bucket ID for feature store offline storage"
  type        = string
}

variable "data_engineer_role_arn" {
  description = "IAM role ARN for Feature Store execution"
  type        = string
}
