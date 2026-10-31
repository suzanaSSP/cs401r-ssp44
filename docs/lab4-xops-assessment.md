# Lab 4: XOps, Testing & CI/CD Pipeline Assessment

## Pipeline Stage Mapping
- Phase 1: Source & Triggering
    - Pulls code from Github when main is pushed using CodeStar connection
    - Extracts COMMIT_SHA
    - RATIONALE: Ensures every build is strictly traceable to a specific commit in version control to be able to reproduce later if needed

- Phase 2: Environment Provising & Dependency Isolation
    - Install necessary libraries from requirements.txt
    - Resolves AWS account & S3 buckets
    - RATIONALE: Updates environments so model and tests can run properly

- Phase 3: Pre-Flight Data & Feature Validation
    - Executes tests for test_data and test_features against S3 dadta
    - Fails for any failed test
    - This is CodeBuild: PRE_BUILD Phase
    - RATIONALE: Validates data is properly cleaned and featured so it doesn't change the model's training. It saves compute cost, if there is an error in the data it halts the building proccess

- Phase 4: Continuos Model Training
    - CodeBuild: Build/ Sagemaker Pipeline
    - Trains model using *northstar-churn-pipeline* 
    - RATIONALE: Training spot instances is less cost and automatically captures training metrics and model artifacts

- Phase 5: Model Quality Gating
    - CodeBuild: BUILD + POST_BUILD/ CodePipeline: Manual Approval
    - Evaluates metrics for trained model
    - Runs test_model.py
    - Models that pass wait for approvel in PendingManualApproval. Someone has to go and approve. 
    - RATIONALE: Running tests on model prevents model regression. PendingManualApproval enforces human-in-the-loop before models can ever serve production to ensure there isn't any other problems not captured by the tests. 