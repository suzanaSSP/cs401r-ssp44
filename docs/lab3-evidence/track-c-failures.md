# Track C: Failure Modes and Mitigations

## Failure Mode 1: Split-Credit Stateless Policy Loophole

- **Test / Trace Reference:** `agent/policy_tests.py` (Test case: split-credit evaluation / `docs/lab3-evidence/policy-tests.json`)
- **Observed Behavior:** If a customer called two $40 credits back to back in different calls, both of them would pass even though it's over the $50 limit. This is because the Cedar Gateway Policy applies the $50 limit per call, but not overall. It's evaluated statelessly and per-invocation
- **Mitigation & Platform Capabilities:**
  - *Mitigation:* Back the credit tool with a DynamoDB ledger tracking cumulative credits per `customer_id` across a sliding window (e.g., 24 hours), rejecting transactions where `cumulative_amount + request_amount > $50`. This would guarantee that the limit is applied per overall use and not per invocation. 

---

## Failure Mode 2: Rewriting Query Retrieved Incorrect Information

- **Test / Trace Reference:** `docs/lab3-evidence/agent-traces.jsonl`
- **sessionID:** "test-TC-002-1792172432-ca49aedb-df00-459b-bb9b-14f88f67e4d3"
- **Observed Behavior:** The customer asked "What is the return window and policy for clothing items like rain jackets?" The agent rewrote the query as "What is the return window and policy for clothing items like rain jackets?" to do the look up. However, the first top-3 hits were not related to the return window policy, and instead were information about warranty, defective items, exchanges, and non-returnable merchandise. This is because the keyword search for 'rain jackets' matched warranty clauses and final-sale lists before the agent had to perform a second query to find the return window policy. The agent rewrote another query which correctly retrived the return window information. 
- **Mitigation & Platform Capabilities:**
  - Upgrade query_policy from lexical BM25 to semantic vector embeddings (Bedrock Titan Embeddings via FAISS or OpenSearch Serverless) so domain entities map to general product return rules rather than keyword-matching warranty clauses.
  - Add instructions for the agent to remove specific product nouns ('rain jacket') to avoid misleading retrievals. 

---