# Metrics & Observability Documentation

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Metric Definitions

### Workers
- **Total Workers**: Count of all registered nodes in database.
- **Active Workers**: Count of workers with `is_active = 1`.
- **Offline Workers**: Count of workers with `is_active = 0`.
- **Busy Workers**: Count of active workers with at least one task assigned with status `'processing'`.
- **Healthy Workers**: Count of workers with health status `'HEALTHY'`.
- **Degraded Workers**: Count of workers with health status `'DEGRADED'`.
- **Unhealthy Workers**: Count of workers with health status `'UNHEALTHY'`.

### Resources
- **Average CPU**: Mean CPU utilization percentage of active workers.
- **Average Available RAM**: Mean available memory in megabytes of active workers.

### Tasks
- **Total Tasks**: Total count of records in tasks table.
- **Processing Tasks**: Count of tasks with status `'processing'`.
- **Completed Tasks**: Count of tasks with status `'completed'`.
- **Failed Tasks**: Count of tasks with status `'failed'`.
- **Total Retries**: Cumulative sum of retry counts across all tasks.

### Reliability
- **Failover Count**: Total logged events in `failover_events` table.
- **Failure Rate**: Percentage of failovers against completed and failed tasks.
- **Retry Rate**: Average number of retries per registered task.
- **Availability Rate**: Ratio of active nodes over total registered.

---

## 2. Calculation & Rate Formulas

### Worker Availability Rate
$$\text{availability\_rate} = \frac{\text{active\_workers}}{\text{total\_workers}}$$
*Denominator: `total_workers`. Evaluates to `0.0` if `total_workers <= 0`.*

### Failure Rate
$$\text{failure\_rate} = \frac{\text{failover\_count}}{\text{completed\_tasks} + \text{failed\_tasks}}$$
*Denominator: Sum of completed and failed tasks. Evaluates to `0.0` if sum is `0`.*

### Retry Rate
$$\text{retry\_rate} = \frac{\text{total\_retries}}{\text{total\_tasks}}$$
*Denominator: `total_tasks`. Evaluates to `0.0` if `total_tasks <= 0`.*

---

## 3. Database Performance Considerations
Rather than executing multiple separate tables query sweeps or transferring raw collections to memory, the `NodeRepository` leverages efficient SQL aggregate statements running inside a single read transaction:
- **Scalability**: Limits DB lock windows. Performs O(1) memory overhead allocations.

---

## 4. API & Flutter Preparation Payload

This structure maps to Phase 8 GET endpoints and Phase 9 Flutter dashboards.

```json
{
  "workers": {
    "total": 3,
    "active": 2,
    "offline": 1,
    "busy": 1,
    "health_states": {
      "healthy": 1,
      "degraded": 1,
      "unhealthy": 1
    },
    "availability_rate": 0.67
  },
  "resources": {
    "avg_cpu": 35.5,
    "avg_ram_mb": 3072.0
  },
  "tasks": {
    "total": 10,
    "processing": 2,
    "completed": 7,
    "failed": 1,
    "total_retries": 4,
    "retry_rate": 0.4
  },
  "reliability": {
    "failover_count": 2,
    "failure_rate": 0.25
  }
}
```
