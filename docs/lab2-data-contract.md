## Data Contract: processed/customers

### Producer
Team / process: Glue ETL job `northstar-dev-transform`

### Consumers
- Feature engineering job `northstar-dev-feature-engineer`
- (Future) Direct model training in Lab 3

### Grain
One row per transaction. A customer appears on many rows.

### Schema
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
|"transaction_id" | string | No | id of a single transaction|
|"customer_id" | string | No | id of customer | 
|"purchase_date" | date | No | date of purchase (yyyy-MM-dd) |
|"order_value" | double | No | cost of purchase in USD (nulls are imputed with median) |
|"num_items" | bigint | No | how many items bought |
|"payment_method" | string | No | how customer paid purchase |
|"channel" | string | No | Online or store (nulls imputed with 'unknown') |
|"store_id" | string | No | store purchased id |
|"product_category" | string | No | topic of product bought | 

### Quality Guarantees
- `customer_id` is never null
- No duplicate `transaction_id` rows (a `customer_id` repeating across rows is expected, not a defect)
- All numeric columns are within expected ranges (`order_value > 0`, `num_items >= 1`)
- `purchase_date` is a valid ISO 8601 date

### SLA
- Data is available in `processed/customers/` within 2 hours of landing in `raw/customers/`

### Versioning
- Schema changes require a new S3 prefix (e.g., `processed/customers/v2/`)
- Breaking changes require consumer notification 5 business days in advance