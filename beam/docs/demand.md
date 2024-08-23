# Demand

This feature computes the what Items are needed and where they are available.

### Demand Map

Demand increases based on the following factors:
- When a Sales Order is submitted
- When a Work Order is submitted

Demand decreases based on the following factors:
- When a Sales Order is either:
  - fulfilled (via a Sales Invoice or a Delivery Note)
  - cancelled
  - closed
  - put on hold
- When a Work Order is either:
  - completed (via a Stock Entry)
  - cancelled
  - closed
  - stopped

<!-- ### Demand-Allocation Report


### Demand API / Workstation Integration
The Demand feature is used by -->
