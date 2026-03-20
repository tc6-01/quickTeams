## ADDED Requirements

### Requirement: Worker completion events are durably persisted before delivery
The system SHALL persist every worker completion event to durable storage before attempting delivery to the lead runtime.

#### Scenario: Persist before dispatch
- **WHEN** a worker reports task completion
- **THEN** the system SHALL write a completion event record before any delivery attempt is made

#### Scenario: Persistence failure blocks dispatch
- **WHEN** durable persistence fails for a worker completion event
- **THEN** the system SHALL not dispatch the event and SHALL return a retriable failure

### Requirement: Lead consumption uses explicit acknowledgment and idempotency
The system SHALL treat a worker completion event as consumed only after an explicit lead acknowledgment and SHALL process duplicate deliveries idempotently by event identifier.

#### Scenario: Event is acknowledged after successful processing
- **WHEN** the lead runtime finishes processing a completion event
- **THEN** the system SHALL mark that event as acknowledged and eligible for stage progression

#### Scenario: Duplicate delivery does not create duplicate side effects
- **WHEN** the same completion event is delivered more than once
- **THEN** the system SHALL recognize the duplicate by event identifier and SHALL not create duplicate downstream work

### Requirement: Unacknowledged completion events are retried and replayed
The system SHALL retry delivery of unacknowledged completion events with bounded backoff and SHALL replay all pending events after lead recovery.

#### Scenario: Unacknowledged event enters retry path
- **WHEN** a completion event is dispatched and no acknowledgment is received within the configured timeout
- **THEN** the system SHALL schedule a retry with bounded backoff

#### Scenario: Pending events are replayed after recovery
- **WHEN** a lead runtime becomes healthy after being unavailable or suspected asleep
- **THEN** the system SHALL replay all unacknowledged completion events for that lead

### Requirement: Lead health is tracked through lease state
The system SHALL maintain lease-based lead health state and SHALL distinguish healthy, suspected sleep, and unavailable states.

#### Scenario: Lead becomes suspected asleep after stale heartbeat
- **WHEN** the lead heartbeat exceeds the configured stale threshold
- **THEN** the system SHALL mark the lead as suspected asleep

#### Scenario: Lead becomes unavailable after recovery timeout
- **WHEN** the lead remains unhealthy beyond the configured recovery timeout
- **THEN** the system SHALL mark the lead as unavailable and trigger recovery evaluation

### Requirement: Stalled team runs are detected and reconciled
The system SHALL detect team runs with no progress beyond the configured hang timeout and SHALL reconcile runtime state against durable state.

#### Scenario: Watchdog detects stalled run
- **WHEN** a team run has no recorded progress for longer than the configured hang timeout
- **THEN** the system SHALL create a reconciliation attempt for that run

#### Scenario: Reconciler repairs mismatch
- **WHEN** reconciliation finds pending durable completion events that are not reflected in runtime state
- **THEN** the system SHALL replay or resume from the last consistent checkpoint

### Requirement: Non-recoverable failures are moved to dead-letter handling with audit context
The system SHALL move non-recoverable events or runs to dead-letter handling and SHALL persist actionable diagnostic context.

#### Scenario: Event exceeds retry limit
- **WHEN** a completion event exceeds the configured retry or recovery limit
- **THEN** the system SHALL move the event to dead-letter handling with team, lead, worker, attempt, and error context

#### Scenario: Recovery action is audited
- **WHEN** the system executes a recovery action such as wake, restart, or handoff
- **THEN** the system SHALL persist an audit record with trigger reason and final status
