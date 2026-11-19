# Architecture Decision Records

This directory records decisions that constrain multiple milestones. A decision should include context, the selected option, alternatives, consequences, and the date/status.

## ADR index

| ID | Decision | Status |
|---|---|---|
| ADR-0001 | Modular monolith with independently testable processing engine | Accepted |
| ADR-0002 | Shared React frontend for web and Tauri desktop | Accepted |
| ADR-0003 | SQLite local-first; PostgreSQL hosted target | Accepted |
| ADR-0004 | Sequential reference runner plus multiprocessing MapReduce | Accepted |
| ADR-0005 | FastAPI job API with SSE progress for initial releases | Accepted |

## ADR-0001 — Modular monolith and engine boundary

**Context:** The product needs clear separation between UI, API orchestration, and compute-heavy processing without the operational burden of distributed services.

**Decision:** Use one deployable API application in `backend/app/` with explicit internal packages. Keep the Python processing engine in `engine/src/cloudlog_engine/` framework-independent and independently testable.

**Alternatives:** Microservices, a single unstructured Python application.

**Consequences:** Local development and deployment stay simple. Package boundaries and dependency direction must be enforced by tests and review.

## ADR-0002 — Shared web and desktop frontend

**Context:** Web and desktop should provide the same product experience and feature behavior.

**Decision:** Use React + TypeScript in `frontend/` for the shared UI and Tauri v2 in `desktop/` as the desktop host.

**Alternatives:** Separate native desktop UI; Electron.

**Consequences:** UI features are implemented once. Desktop OS integration stays behind Tauri capabilities and a narrow host bridge.

## ADR-0003 — Local SQLite and hosted PostgreSQL

**Context:** Local privacy-first usage should work without a database server, while hosted multi-user deployment needs a robust relational database.

**Decision:** SQLite is the local/desktop default; PostgreSQL is the hosted target. Use SQLAlchemy and Alembic for the persistence boundary and schema evolution.

**Consequences:** Database-specific behavior must be tested. SQLite writes are serialized through one owner process; multiprocessing engine workers do not write directly to the database.

## ADR-0004 — Deterministic MapReduce execution

**Context:** Users need large-file processing, a clear MapReduce learning/inspection surface, and confidence that parallel execution does not change results.

**Decision:** Maintain a sequential reference implementation and a multiprocessing implementation with bounded chunks/queues and disk spill. Both must satisfy the same reducer contracts and equivalence tests.

**Alternatives:** Sequential-only processing; premature Hadoop dependency.

**Consequences:** Deterministic partitioning, stable aggregation semantics, resource limits, and cleanup guarantees are core requirements. Hadoop/HDFS integration remains a later adapter, not a dependency of the MVP.

## ADR-0005 — Job resources and SSE progress

**Context:** Large analysis jobs outlive ordinary HTTP request durations.

**Decision:** API requests create job resources. Clients observe status and progress through Server-Sent Events initially; the job executor owns lifecycle and cancellation.

**Alternatives:** Long-running synchronous requests; a broker-backed distributed worker system from day one.

**Consequences:** Job state transitions must be explicit and idempotent. SSE is a progress channel, not the source of truth; clients can reconnect and fetch the job resource.
