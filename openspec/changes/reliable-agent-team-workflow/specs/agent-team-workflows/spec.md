## ADDED Requirements

### Requirement: Team workflows are launched through a unified entrypoint
The system SHALL provide a unified workflow entrypoint that starts an agent team run from a named workflow template.

#### Scenario: Start workflow run by template name
- **WHEN** an operator invokes the workflow entrypoint with a workflow name
- **THEN** the system SHALL load the corresponding workflow template and initialize a new team run

### Requirement: Workflow templates define ordered stages and ownership
The system SHALL represent each team workflow as an ordered set of stages with assigned owner roles, instructions, success criteria, and failure handling rules.

#### Scenario: Stage definition includes execution contract
- **WHEN** a workflow template is loaded
- **THEN** each stage SHALL include its owner role, stage instructions, success criteria, and failure policy

#### Scenario: Stages execute in dependency order
- **WHEN** a team run starts
- **THEN** the system SHALL execute stages only after their declared predecessors are complete

### Requirement: Stage progression is managed by durable run state
The system SHALL persist run state and stage state so that workflow progression does not depend solely on lead in-memory context.

#### Scenario: Run state is created at workflow start
- **WHEN** a new team workflow run is initialized
- **THEN** the system SHALL persist run state including workflow name, current stage, stage status, and participating agents

#### Scenario: Stage completion updates durable state
- **WHEN** a stage is completed successfully
- **THEN** the system SHALL persist the completed stage and next stage transition in durable state

### Requirement: Checkpoints allow workflow resumption after interruption
The system SHALL persist checkpoints that allow an interrupted workflow run to resume from the last consistent state.

#### Scenario: Checkpoint is saved on progress boundary
- **WHEN** a stage starts, completes, or transitions state
- **THEN** the system SHALL update the workflow checkpoint

#### Scenario: Workflow resumes from checkpoint after recovery
- **WHEN** a run is restored after lead recovery, restart, or handoff
- **THEN** the system SHALL resume from the latest consistent checkpoint instead of restarting the workflow from the beginning

### Requirement: Hooks enforce workflow guardrails without owning workflow state
The system SHALL allow lifecycle hooks to inject workflow instructions, audit progress, and trigger checks, but SHALL keep workflow truth in runtime and durable state.

#### Scenario: Pre-run hook injects workflow SOP
- **WHEN** a workflow run is started
- **THEN** the system SHALL allow a pre-run hook to inject standard execution guardrails for the selected workflow

#### Scenario: Hook does not replace durable workflow state
- **WHEN** a hook runs during workflow execution
- **THEN** the system SHALL not rely on hook-local state as the sole source of workflow progression
