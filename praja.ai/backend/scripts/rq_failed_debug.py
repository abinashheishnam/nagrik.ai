from __future__ import annotations
import os
import sys

# Ensure backend root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis import Redis
from rq import Queue
from rq.registry import FailedJobRegistry
from app.utils.queue import get_queue, get_redis

def main():
    print(">>> Connecting to Redis...")
    r = get_redis()
    q = get_queue('praja')
    
    registry = FailedJobRegistry(queue=q)
    failed_job_ids = registry.get_job_ids()
    
    count = len(failed_job_ids)
    print(f">>> Found {count} failed jobs in 'praja' queue registry.")

    if not failed_job_ids:
        print(">>> No failed jobs. All good!")
        return

    # Show last 5
    for job_id in failed_job_ids[-5:]:
        job = q.fetch_job(job_id)
        if not job:
            print(f"\n[Job {job_id}] - Not found in Redis (expired?)")
            continue
        
        print(f"\n" + "-"*60)
        print(f"JOB ID: {job.id}")
        print(f"FUNC: {job.func_name}")
        print(f"ARGS: {job.args}")
        print(f"CREATED: {job.created_at}")
        print(f"FAILED: {job.ended_at}")
        print(f"EXC INFO (Tail):")
        if job.exc_info:
            print(job.exc_info[-500:]) # Last 500 chars of stack trace
        else:
            print("(No exception info)")
        print("-" * 60)

if __name__ == "__main__":
    main()
