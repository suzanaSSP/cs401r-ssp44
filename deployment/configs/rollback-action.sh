#!/bin/bash
set -e

# Configuration variables
ENDPOINT_NAME="your-sagemaker-endpoint-name"
PRODUCTION_VARIANT_NAME="AllTrafficVariant"
CANARY_VARIANT_NAME="CanaryVariant"

echo "Initiating rollback procedure for endpoint: $ENDPOINT_NAME..."

# Update the endpoint weights to shift all traffic back to the production variant and 0 to canary
aws sagemaker update-endpoint-weights-and-capacities \
    --endpoint-name "$ENDPOINT_NAME" \
    --desired-weights-and-capacities \
        VariantName="$PRODUCTION_VARIANT_NAME",Weight=1 \
        VariantName="$CANARY_VARIANT_NAME",Weight=0

echo "Rollback command sent successfully. Waiting for endpoint to update..."

# Wait for the endpoint to return to the InService status (typically takes ~90 seconds)
aws sagemaker wait endpoint-in-service --endpoint-name "$ENDPOINT_NAME"

echo "Rollback completed. Endpoint is back InService and canary traffic is set to 0."