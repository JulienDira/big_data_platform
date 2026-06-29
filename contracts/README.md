# Data contracts

`market-candle/v1.avsc` is the only canonical candle contract. Producers and
consumers load this file at runtime; they must not maintain private copies.

Schema Registry compatibility is set to `BACKWARD`. Additive changes require
nullable fields or defaults. Breaking changes require a new subject/topic
version rather than an in-place edit.

