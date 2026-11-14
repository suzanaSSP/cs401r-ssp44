## Lab4 -> saving logs in docs/lab4-build-green.logs:

1. Build 
```
aws codepipeline start-pipeline-execution \
  --name northstar-pipeline \
  --region us-east-1
```
2. Get status

```
EXECUTION_ID=$(aws codepipeline start-pipeline-execution \
  --name northstar-pipeline \
  --region us-east-1 \
  --query 'pipelineExecutionId' --output text)

aws codepipeline get-pipeline-execution \
  --pipeline-name northstar-pipeline \
  --pipeline-execution-id "$EXECUTION_ID" \
  --region us-east-1 \
  --query 'pipelineExecution.[status,startTime]' \
  --output table

aws codepipeline get-pipeline-execution \
  --pipeline-name northstar-pipeline \
  --pipeline-execution-id "c9159c9f-fb60-4047-ba75-7b90b07fce90" \
  --region us-east-1 \
  --query 'pipelineExecution.[status,startTime]' \
  --output table
```
3. Run output in log
```
save_log () {
  local G S
  read -r G S <<< "$(aws codebuild batch-get-builds --ids "$1" \
    --query 'builds[0].logs.[groupName,streamName]' --output text)"
  aws logs filter-log-events --log-group-name "$G" --log-stream-names "$S" --output json \
    | python3 -c 'import json,sys; sys.stdout.write("".join(e["message"] if e["message"].endswith("\n") else e["message"]+"\n" for e in json.load(sys.stdin)["events"]))' \
    > "$2"
}

B=$(aws codebuild list-builds-for-project \
  --project-name northstar-ci \
  --sort-order DESCENDING \
  --region us-east-1 \
  --query 'ids[0]' --output text)

aws codebuild batch-get-builds \
  --ids "$B" \
  --region us-east-1 \
  --query 'builds[0].[id,buildStatus,startTime]' \
  --output table

save_log "$B" docs/lab4-build-green4.log
```

4. Stop Pipeline
```
aws codepipeline stop-pipeline-execution \
  --pipeline-name northstar-pipeline \
  --pipeline-execution-id "22c97ada-ebf8-466a-9453-fe899faf3ca5" \
  --region us-east-1 \
  --no-abandon \
  --reason "Stopping duplicate runs"
```

5. List models
```
aws sagemaker list-model-packages \
  --model-package-group-name northstar-churn-models \
  --query 'ModelPackageSummaryList[*].[ModelPackageVersion,ModelApprovalStatus,ModelPackageArn]' \
  --output table
```

6. Describe model:
```
aws sagemaker describe-model-package \
  --model-package-name model-package/northstar-churn-models/13 \
  --query '{Version:ModelPackageVersion,Status:ModelApprovalStatus,Metrics:CustomerMetadataProperties}' \
  --output json
```
7. Approve as champion model
```
aws sagemaker update-model-package \
  --model-package-arn "arn:aws:sagemaker:us-east-1:$(aws sts get-caller-identity --query Account --output text):model-package/northstar-churn-models/13" \
  --model-approval-status "Approved" \
  --approval-description "Approved as champion model: AUC-ROC 0.7855, Precision@10 0.7167, Recall@10 0.3258, Lift CI [0.0455, 0.0839]"
```
8. Get quotas for instace:
```
# ml.t2.medium
aws service-quotas get-aws-default-service-quota \
  --service-code sagemaker --quota-code L-29C181D7 \
  --region us-east-1 --query 'Quota.Value' --output text
```

9. Create model from package:
```
aws sagemaker create-model \
  --model-name northstar-churn-model-v1-approved \
  --primary-container ModelPackageName="arn:aws:sagemaker:us-east-1:042186225029:model-package/northstar-churn-models/13" \
  --execution-role-arn "arn:aws:iam::042186225029:role/northstar-dev-MLEngineer"
```

10. List endpoints:
```
aws sagemaker list-models --region us-east-1
```

11. Create endpoint:
```
aws sagemaker create-endpoint \
  --endpoint-name northstar-churn-prod \
  --endpoint-config-name northstar-churn-prod-config-m5 \
  --region us-east-1
```
- Wait until it's live
```
aws sagemaker wait endpoint-in-service \
  --endpoint-name northstar-churn-prod \
  --region us-east-1
```




Notes: 
northstar-ci:629ff630-8ecb-48aa-b99e-07eeab269cbf

# Upload sample data
aws s3 cp northstar-raw-sample.csv \
  s3://northstar-dev-data-$(aws sts get-caller-identity --query Account --output text)/raw/customers/northstar-raw-sample.csv

# Run the crawler (waits for completion)
aws glue start-crawler --name northstar-dev-raw-crawler
aws glue get-crawler --name northstar-dev-raw-crawler --query 'Crawler.State'

# Verify the table was created
aws glue get-table --database-name northstar_dev --name customers

# Run the transform job
aws glue start-job-run --job-name northstar-dev-transform
aws glue get-job-run --job-name northstar-dev-transform \
  --run-id $(aws glue get-job-runs --job-name northstar-dev-transform \
    --query 'JobRuns[0].Id' --output text)

# 6. Check that the job SUCCEEDED
aws glue get-job-runs --job-name northstar-dev-transform --query 'JobRuns[0].JobRunState'

# 7. Check the Parquet output in S3
aws s3 ls s3://northstar-dev-data-$(aws sts get-caller-identity --query Account --output text)/processed/customers/ --recursive

  # OR do this Verify processed output
  aws s3 ls s3://northstar-dev-data-ACCOUNT_ID/processed/customers/ --recursive

and
# Run feature engineering job
aws glue start-job-run --job-name northstar-dev-feature-engineer

# Verify features written to S3
aws s3 ls s3://northstar-dev-data-042186225029/features/customers/ --recursive

(optional)
aws s3 ls s3://northstar-dev-data-$(aws sts get-caller-identity --query Account --output text)/processed/customers/ --recursive

# Verify Feature Store records (after job completes — offline store has ~15 min lag)
aws sagemaker describe-feature-group --feature-group-name northstar-dev-customer-features


Version	Status	AUC-ROC	Precision @ 10%	Recall @ 10%	Lift 95% CI	Verdict
13	PendingManualApproval	0.7855	0.7167	0.3258	[0.0455, 0.0839]	🏆 Best Performing
2	PendingManualApproval	0.7820	0.7100	0.3227	[0.0408, 0.0777]	Strong runner-up
1	PendingManualApproval	0.7764	0.6900	0.3136	[0.0331, 0.0731]	Baseline model
3	PendingManualApproval	0.7662	0.6867	0.3121	[0.0212, 0.0633]	Regressed
11	Approved	N/A (in S3)	N/A	N/A	N/A	Prior champion placeholder
