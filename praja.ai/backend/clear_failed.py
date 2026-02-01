from redis import Redis
from rq import Queue
from rq.registry import FailedJobRegistry

r = Redis(host="localhost", port=6379, db=0)
q = Queue("praja", connection=r)

reg = FailedJobRegistry(queue=q)
ids = reg.get_job_ids()

print("Failed jobs found:", len(ids))
for jid in ids:
    reg.remove(jid, delete_job=True)

print("Failed registry cleared.")
