## Demand Design

### SQLite
Beam uses SQLite in parallel with MariaDB for specific data separation and performance optimization.

**Architecture Pattern:**
- Beam maintains dual database connections:
  - MariaDB (via Frappe): Core ERP data, transactions, master data
  - SQLite: Demand planning, receiving operations, analytics

**Demand and Receiving Tables:**
- **Demand Planning Data**: SQLite stores demand forecasting calculations and planning data
- **Receiving Operations**: Real-time receiving data and processing queues
- **Separation of Concerns**: Isolates high-frequency demand operations from core ERP data
- **Performance Benefits**: Faster read/write operations for demand-specific workloads

**Use Cases:**
- Demand forecasting calculations
- Receiving workflow data
- Temporary processing queues
- Analytics and reporting aggregations
