# Kubernetes reference

`distributed-worker.yaml` is an integration template, not a ready-made PyAgentsKit server.
The embedding application must implement the three HTTP endpoints and connect them to
`DistributedWorkerController.health()` and `drain()`.

Replace the placeholder image, configure PostgreSQL credentials through the platform secret
mechanism and validate TTL/grace values with production latency measurements. The pod UID provides
a unique worker-incarnation owner ID. Queue consumption must stop before the drain endpoint waits.
