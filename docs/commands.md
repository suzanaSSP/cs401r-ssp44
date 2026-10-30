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

save_log "$B" docs/lab4-build-green.log
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

# Verify processed output
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