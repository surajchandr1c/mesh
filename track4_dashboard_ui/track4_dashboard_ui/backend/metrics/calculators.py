from __future__ import annotations


def calculate_availability_rate(active_workers: int, total_workers: int) -> float:
    """Calculate the ratio of active workers against the total registered.

    Formula:
        availability = active_workers / total_workers

    Zero-division:
        If total_workers is 0, returns 0.0.
    """
    if total_workers <= 0:
        return 0.0
    return float(active_workers) / float(total_workers)


def calculate_failure_rate(failover_count: int, completed_tasks: int, failed_tasks: int) -> float:
    """Calculate task failure/failover rate against completed and failed tasks.

    Formula:
        failure_rate = failover_count / (completed_tasks + failed_tasks)

    Zero-division:
        If completed_tasks + failed_tasks is 0, returns 0.0.
    """
    denominator = completed_tasks + failed_tasks
    if denominator <= 0:
        return 0.0
    return float(failover_count) / float(denominator)


def calculate_retry_rate(total_retries: int, total_tasks: int) -> float:
    """Calculate the average number of retries per task.

    Formula:
        retry_rate = total_retries / total_tasks

    Zero-division:
        If total_tasks is 0, returns 0.0.
    """
    if total_tasks <= 0:
        return 0.0
    return float(total_retries) / float(total_tasks)
