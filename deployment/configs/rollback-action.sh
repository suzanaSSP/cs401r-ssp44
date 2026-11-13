#!/bin/bash
set -e

REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ENDPOINT_NAME="northstar-churn-prod"
PRODUCTION_VARIANT_NAME="champion"
CANARY_VARIANT_NAME="canary"

echo "Initiating rollback procedure for endpoint: $ENDPOINT_NAME..."

# Update the endpoint weights to shift all traffic back to the production variant and 0 to canary
aws sagemaker update-endpoint-weights-and-capacities \
    --region "$REGION" \
    --endpoint-name "$ENDPOINT_NAME" \
    --desired-weights-and-capacities \
        VariantName="$PRODUCTION_VARIANT_NAME",DesiredWeight=1 \
        VariantName="$CANARY_VARIANT_NAME",DesiredWeight=0

echo "Rollback command sent successfully. Waiting for endpoint to update..."

# Wait for the endpoint to return to the InService status (typically takes ~90 seconds)
aws sagemaker wait endpoint-in-service --region "$REGION" --endpoint-name "$ENDPOINT_NAME"

echo "Rollback completed. Endpoint is back InService and canary traffic is set to 0."