Canary -> version 13
Champion -> version 11

## Deployment Plan

### Deployment strategy and rationale — why this strategy for this system?
I used the Real-Time Endpoint deployment strategy. I chose this strategy because it fits the design for a churn model. If I used a batch transform, I would run the data once on a certain time period for all the customers, and update their churn scores. By the time it was updated, the high risk churners may have already canceled their subscription and churned. With a real time endpoint, the model can identify when something happens that may cause a customer to churn (damaged package, dissatisfaction, etc.) and propose a needed action to keep the customer. This could be an offer or customer support. Having a model always updating its customer’s churn scores is important for these scenarios. 

I used the champion/canary deploying method for serving the Real-Time Endpoint. I used this because it’s a way to test whether the new proposed model has any bugs or problems that were not detected during training. If it crashes or causes any problems, only 10% of the customers will be affected (Canary) and the other 90% will continue with the model that already works. There are other methods like blue/green, shadowing, and all at once. Blue/green, and Shadowing can cost a lot because it’s running twice the computer time, while All-At-Once is very risky to run the new model to 100% of customers. Champion/Canary seemed to be the best option. 


### Pre-deployment checklist — what must be true before the deployment begins? Include the model-approval step and who performs it.
Before beginning the deployment, these things need to happen/be true:

    - Make sure the data that will be used it in S3 buckets and has been processed and featured engineered (CI/CD Pipeline does this verification)
    - Approve Champion and canary models from PendingManualApproval to Approved. (MLEngineeer does that)
    - Have enough instance quotas for chosen instances (ml.t2.medium or ml.m5.large)
    - Create endpoint-config-canary.json file that specific how much traffic each Champion and Canary model will receive
    - Create rollback-action.sh to rollback if needed
    - Create endpoint of canary and champion model
    - Have CloudWatch and SNS notifications enabled so engineers are alerted when something happens to the Canary or Champion model. 

### Rollback criteria — exact metric, exact threshold, who makes the call

If it has any of these things, it rolls back:

    - ModelLatency > 200000 microseconds
    - System Errors like InvocationErrors, or error_rate > 1%
    - Currently there’s a rollback-action file that does runs aws sagemaker update-endpoint-weights-and-capacities to instantly shift the canary weight to 0.0 and restore champion to 1.0 without any endpoint downtime. A manual intervention would happen to do the roll-back.


### Monitoring window — how long, what you are watching, what constitutes a clean deployment, and the lab-vs-production compression from Task 1

In production, models are usually up in this champion-canary style for 48 hours. For this lab we only had it up for 60 minutes. We are looking for the amount of traffic throughout the day and how the model performs. 

A clean deployment is when there are zero 5XX errors, p95 latency under 200ms, and minimum invocation volume reached without alarm triggers.

Because for this lab the model was only deployed for 1 hour, there wasn't a way to detect trends in traffic throughout the day, while in a 48 hour production, it would be able to receive more information throughout the day of how the model performed. However, having it deployed for less time made the cost much cheaper. 

### Stakeholder notifications — who gets notified at each stage (deployment start, promotion, rollback)
MLEngineer and business people

- **Stage 1: Deployment Start (Canary Launch at 90/10 split)**
  - *Who:* ML Engineering team, MLOps / SRE on-call.
  - *Channels & Content:* Automated notification sent via Slack/SNS detailing endpoint name (`northstar-churn-prod`), model package versions (Champion v11 vs. Canary v13), traffic weights (90.0 / 10.0), and a link to the CloudWatch monitoring dashboard.
- **Stage 2: Promotion (Canary Success / 100% Traffic)**
  - *Who:* ML Engineer, MLOps, and Business Stakeholders (Customer Retention Team, CRM Product Managers).
  - *Channels & Content:* Email and Slack announcement confirming the canary completed the monitoring window cleanly and is promoted to 100% active Champion, with the previous model version retired.
- **Stage 3: Rollback (Threshold Breach or Anomaly)**
  - *Who:* On-call ML Engineer, SRE, and Business Stakeholders.
  - *Channels & Content:* High-priority PagerDuty/SNS alert stating that CloudWatch alarm triggered (e.g., `ModelLatency > 200ms`), canary traffic was shifted back to 0.0 (100% Champion), and triage runbooks are attached.

### Post-deployment review — when it happens, who attends, what artifact it produces

- **When it happens:** Scheduled 24 to 48 hours after full production promotion (or within 24 hours as an incident post-mortem if a rollback was triggered).
- **Who attends:** 
  - Lead ML Engineer (who trained and registered the model)
  - Data Engineer (who manages upstream pipelines and feature engineering)
  - MLOps / DevOps Platform Engineer (responsible for serving infrastructure and alarms)
  - Product Manager / Business Stakeholder (Customer Retention Lead)
- **Artifact produced:** 
  - **Deployment Retrospective Report** (or Incident Post-Mortem in case of rollback).
  - *Contents of the artifact:*
    - Production volume summary and observed latency percentiles (p50, p95, p99).
    - Comparison of canary vs. champion churn prediction distributions (verifying no score drift).
    - Total AWS infrastructure cost incurred during canary testing and steady state.
    - Updated SageMaker Model Registry status (confirming v13 tagged as active Champion and v11 archived).
    - Action items and lessons learned for subsequent model training iterations.

### Resource cleanup — which resources are deleted after the monitoring window, in what order, and how cleanup is verified

- **Which resources are deleted:**
  1. Application Auto Scaling policies and Scalable Targets
  2. CloudWatch Alarms (`NorthStarModelLatencyRollbackAlarm`)
  3. SageMaker Endpoint (`northstar-churn-prod`)
  4. SageMaker Endpoint Configuration (`northstar-churn-prod-config`)
  5. SageMaker Models (`northstar-churn-model-v1-approved`, `northstar-churn-model-v2`)
  *(Note: SageMaker Model Registry entries are metadata only and cost nothing, so they are kept for auditability and lineage).*

- **Strict Deletion Order (Dependency Chain):**
  Due to AWS resource dependencies, resources must be deleted from top to bottom:
  1. **Auto-scaling & Alarms first:** Deregister scalable targets (`deregister-scalable-target`) and delete CloudWatch alarms so alarms do not fire false positives during teardown.
  2. **SageMaker Endpoint second:** Delete the endpoint (`delete-endpoint`). AWS will not allow deleting endpoint configurations or models while an active endpoint is referencing them.
  3. **Endpoint Configuration third:** Delete the endpoint config (`delete-endpoint-config`) once the endpoint enters terminated state.
  4. **SageMaker Models fourth:** Delete the underlying model entities (`delete-model`).

- **How cleanup is verified:**
  - Verified by running AWS CLI inspection commands:
    - `aws sagemaker list-endpoints` -> confirms 0 endpoints in service.
    - `aws sagemaker list-endpoint-configs` -> confirms 0 endpoint configs.
    - `aws application-autoscaling describe-scalable-targets --service-namespace sagemaker` -> confirms 0 targets.
  - Review AWS Cost Explorer / CloudWatch Metrics to verify that instance hours for `ml.t2.medium` / `ml.m5.large` have ceased and no billable compute resources remain running.
