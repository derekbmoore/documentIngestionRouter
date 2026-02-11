# Multi-Tenant Resource Security

The Document Ingestion Router enforces a **Defense-in-Depth** security model, aligned with **NIST AI RMF** and **FedRAMP High** baselines.

## 1. 4-Layer Security Context

Every request is scoped by a `SecurityContext` that carries:

- **Tenant Identity**: Strict data isolation.
- **User Identity**: RBAC roles (`admin`, `editor`, `viewer`).
- **Project Scope**: Optional project-level isolation.
- **ACL Groups**: Team-based access control.

## 2. Resource Access Policy (RAP)

We enforce a unified **Resource Access Policy** at the SQL level for all data types (Documents, Chunks, Graph Nodes, Connectors).

| Access Level | Description |
|---|---|
| `private` | Accessible only by the owner. |
| `team` | Accessible by users sharing an ACL group. |
| `project` | Accessible by users in the same project. |
| `tenant` | Accessible by all users in the tenant. |

## 3. Audit Logging (NIST AI RMF)

All access events are logged with structured JSON:

```json
{
  "event_type": "resource.access",
  "action": "ingest",
  "user_id": "user-123",
  "tenant_id": "tenant-a",
  "outcome": "success",
  "timestamp": "2024-02-11T20:00:00Z"
}
```

## 4. Graph Security

Knowledge graph traversals are strictly scoped to the caller's tenant. Nodes and edges inherit the security level of their source documents.
