# AWS batch orchestration

Terraform stack for the scheduled AWS batch chain after Raw ingestion.

It creates:

- a Step Functions Standard state machine;
- an EventBridge Scheduler trigger;
- a DynamoDB single-flight lock table with TTL;
- IAM roles for Scheduler and Step Functions;
- a CloudWatch log group for state-machine execution logs.

Runtime flow:

```text
EventBridge Scheduler rate(1 minute)
-> Step Functions
-> DynamoDB conditional lock
-> Glue Bronze batch
-> Glue Silver batch
-> Glue Gold/trading_gold batch
-> latest projection Lambda
-> DynamoDB latest metrics
```

`Kinesis -> Raw S3` remains the Glue Streaming path declared in
`infra/aws/batch`.

The schedule is disabled by default. Keep
`batch_pipeline_schedule_enabled = false` until the AWS bootstrap, deployment
and controlled runtime validation have succeeded.
