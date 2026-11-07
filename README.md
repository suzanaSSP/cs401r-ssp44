# cs401r-lab1-template
CS 401R Lab 1: Platform Foundation — starter template (do not fork directly)

# cs401r-lab2-template
CS 401R Lab 2: Data &amp; Feature Engineering — starter template (do not fork directly)

# NorthStar ML Platform — Lab 2: Data & Feature Engineering

This repository contains the infrastructure and data pipelines for **Lab 2**, building on the foundational architecture from Lab 1. In this lab, we harden the cloud infrastructure by moving SageMaker into a private subnet behind a NAT Gateway, implement automated S3 lifecycle rules, establish secure least-privilege IAM roles, and build a full end-to-end data processing and feature engineering pipeline using AWS Glue and SageMaker Feature Store.

---

## 🏗️ New Modules & Architecture Additions

Lab 2 extends your existing Terraform codebase with the following components:

### 1. VPC Networking (`modules/vpc/`)
* **Private Subnet (`northstar-dev-private-1`):** Hosts the SageMaker Domain and Glue job workers securely.
* **NAT Gateway (`northstar-dev-nat`):** Deployed in the public subnet (`northstar-dev-public-1`) with an Elastic IP to allow outbound-only internet access for private resources (e.g., pulling container images and calling AWS APIs).
* **Private Route Table:** Routes outbound internet traffic (`0.0.0.0/0`) through the NAT Gateway.
* **Self-Referencing Security Group Rule:** An ingress rule (`self = true`) added to the SageMaker/Glue security group, which is strictly required by AWS Glue to initialize jobs inside a VPC.

### 2. Storage & Lifecycle Policies (`modules/storage/`)
* **S3 Lifecycle Rules:** Automatically prunes old data and old object versions to optimize storage costs:
  * `expire-raw-data`: Deletes current versions in `raw/` after 90 days.
  * `expire-raw-versions`: Deletes noncurrent versions in `raw/` after 30 days.
  * `expire-processed-versions`: Deletes noncurrent versions in `processed/` after 30 days.
  * `expire-feature-versions`: Deletes noncurrent versions in `features/` after 60 days.
  * `expire-datacapture`: Deletes current versions in `datacapture/` after 7 days (anticipating Lab 5 model monitoring).

### 3. Identity and Access Management (`modules/iam/`)
* **`northstar-dev-DataEngineer`:** Trusted by Glue, Lambda, and SageMaker. Granted full access to Glue databases/crawlers/jobs, S3 read/write access on `raw/`, `processed/`, and `features/`, read-only access to `artifacts/glue/`, and Feature Store mutations.
* **`northstar-dev-ModelMonitor`:** Trusted by SageMaker to observe drift metrics, read from `artifacts/`, and write logs/metrics to CloudWatch.

### 4. Data Ingestion & Glue Pipelines (`modules/glue/`)
* **Glue Catalog Database (`northstar_dev`)** & **Raw Crawler (`northstar-dev-raw-crawler`)**: Automatically scans `raw/customers/` and registers the schema.
* **Transform Job (`northstar-dev-transform`)**: A Glue 4.0 Spark job that casts data types, imputes null values, deduplicates records based on `transaction_id`, and writes cleaned Parquet files to `processed/customers/`.
* **Feature Engineering Job (`northstar-dev-feature-engineer`)**: Splits transaction data temporally (observation vs. outcome windows), computes 13 churn-predictive features, derives customer loyalty tiers, and writes records both to S3 (`features/customers/`) and the SageMaker Feature Store.

### 5. SageMaker Feature Store (`modules/feature_store/`)
* **Feature Group (`northstar-dev-customer-features`)**: Configured with `customer_id` as the record identifier and `event_time` (epoch seconds) as the event time. Enables both the **Online Store** (for real-time inference) and the **Offline Store** (backed by S3).

---

## 🚀 Running the Data Pipeline End-to-End

Execute the following steps from your terminal to provision infrastructure, ingest data, and run the transformation and feature engineering pipelines.

### Step 1: Apply Terraform Infrastructure
```bash
cd infrastructure/environments/dev
terraform plan
terraform apply 2>&1 | tee ../../../docs/lab2-extend-output.txt