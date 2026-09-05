# SAMVED Role & Authorization Matrix (RBAC & IDOR)

## 1. Role Definitions
- **OPERATOR**: Frontline responder handling live intake, case notes, safety assessment review, and sandbox training.
- **SUPERVISOR**: Operations lead with authority to override escalations, review all districts, approve data purges, and trigger emergency actions.
- **DISTRICT_ADMIN**: Administrative analyst restricted strictly to aggregated reporting and case intelligence for their assigned district.
- **AUDITOR**: Oversight official with read-only access to audit logs, compliance reports, and simulation benchmarks.
- **SYSTEM_ADMIN**: Platform engineer with system-level configuration and maintenance permissions.

## 2. Granular Permissions Mapping

| Permission | OPERATOR | SUPERVISOR | DISTRICT_ADMIN | AUDITOR | SYSTEM_ADMIN |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `cases:read` | Assigned | Global | Assigned District | No | Global |
| `cases:write` | Assigned | Global | No | No | Global |
| `calls:handle` | Yes | Yes | No | No | Yes |
| `calls:dispatch_override` | No | Yes | No | No | Yes |
| `alerts:override` | No | Yes | No | No | Yes |
| `alerts:acknowledge` | Yes | Yes | No | No | Yes |
| `audit:read` | No | Yes | District | Yes | Yes |
| `audit:export` | No | Yes | No | Yes | Yes |
| `analytics:read` | No | Yes | District | Yes | Yes |
| `districts:read` | No | Yes | District | No | Yes |
| `districts:write` | No | No | District | No | Yes |
| `simulation:read` | Yes (Sandbox) | Yes | No | Yes | Yes |
| `simulation:write` | No | Yes | No | No | Yes |
| `retention:manage` | No | Yes | No | No | Yes |

## 3. IDOR & District Boundary Rules
1. **District Isolation**: If `UserIdentity.role == DISTRICT_ADMIN`, all database queries and API actions enforce `WHERE district_code = :user_district`. Any request for a different district returns HTTP 403 Forbidden.
2. **Operator Isolation**: An operator can only modify cases where `assigned_operator_id = :user_id` or unassigned intake cases. Modifying another operator's case requires supervisor reassignment.
3. **Simulation Quarantine**: Simulation test runners execute with synthetic tags. Any write operation from a simulation session directed at production case tables is rejected with HTTP 403.
