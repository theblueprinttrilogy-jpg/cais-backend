# Architecture - CAIS Code Compliance

## High-Level Architecture

+-----------------------------------------------------------+
|                    API Gateway (FastAPI)                    |
+---------------------------+-------------------------------+
                            |
+---------------------------+-------------------------------+
|                          Agents                             |
|  +-------------+ +-------------+ +-----------------------+ |
|  |PlanInspector| | CodeMatcher | |JurisdictionOrchestrator| |
|  +-------------+ +-------------+ +-----------------------+ |
|  +-------------+ +-------------+ +-----------------------+ |
|  |ReportGenerator|ChameleonEngine| |  SelfHealingSystem   | |
|  +-------------+ +-------------+ +-----------------------+ |
+---------------------------+-------------------------------+
                            |
+---------------------------+-------------------------------+
|                     Core Services                           |
|  +-------------+ +-------------+ +-----------------------+ |
|  |  Database   | |   Redis     | |      RabbitMQ         | |
|  |(PostgreSQL) | |   Cache     | |    Message Queue      | |
|  |  + pgvector | |             | |                       | |
|  +-------------+ +-------------+ +-----------------------+ |
+-----------------------------------------------------------+

## Components

### 1. API Gateway (FastAPI)
- RESTful API endpoints
- JWT authentication
- Rate limiting
- Request/Response validation

### 2. Agents

#### PlanInspector
- PDF to images conversion (200 DPI)
- OCR text extraction
- Pattern detection (door widths, keywords)
- Evidence capture with red rectangles

#### CodeMatcher
- pgvector embeddings for semantic search
- 8 code sources (IBC, NFPA, ADA, OSHA, Local, State, Federal, Industry)
- Yellow highlighting on matched code sections

#### JurisdictionOrchestrator
- Address parsing and validation
- Jurisdiction identification
- Code set retrieval for specific locations

#### ReportGenerator
- 4-column evidence table
- Screenshots with red rectangles
- Code screenshots with yellow highlighting
- Legal disclaimer

#### ChameleonEngine
- Visual adaptation for 21 marketplaces
- Skin loading and caching
- Language translation

#### SelfHealingSystem
- Continuous monitoring of all agents
- Failure detection and root cause analysis
- Automatic healing without human intervention

### 3. Data Storage

#### PostgreSQL with pgvector
- Primary relational database
- Vector embeddings for semantic search
- Full-text search capabilities

#### Redis
- API response caching
- Session management
- Rate limiting counters

#### RabbitMQ
- Asynchronous task processing
- Event-driven architecture
- Background job execution

### 4. Security Components

#### WORM Ledger
- Write Once, Read Many
- Cryptographic hashing
- Timestamp verification

#### SecurityGuard
- IP blocking
- SQL injection prevention
- Suspicious pattern detection

#### Kill Switch
- Emergency operation termination
- Container destruction
- File cleanup

### 5. CI/CD Pipeline (GitHub Actions)
- Automated build on push to main
- Docker image creation and push
- Deployment to Cloud Run

## Data Flow

### Document Analysis Flow
1. User uploads PDF
2. PlanInspector converts to images (200 DPI)
3. OCR extracts text
4. Address and jurisdiction extracted
5. CodeMatcher searches for violations
6. Evidence captured (screenshots)
7. ReportGenerator creates Forensic Facts Dossier
8. WORM Ledger records the action

### Authentication Flow
1. User registers
2. 30-day free trial starts
3. User logs in
4. JWT tokens generated
5. Tokens used for API access
6. Subscription checked on each request

## Deployment Architecture (GCP)

+-----------------------------------------------------------+
|                      Google Cloud Run                       |
|  +-----------------------------------------------------+ |
|  |                 cais-backend                         | |
|  |         (4Gi RAM, 2 CPU, 10 max instances)          | |
|  +-----------------------------------------------------+ |
+---------------------------+-------------------------------+
                            |
+---------------------------+-------------------------------+
|                    Cloud SQL (PostgreSQL)                  |
|                    (pgvector extension)                    |
+-----------------------------------------------------------+

## Performance Considerations

- Horizontal scaling via Cloud Run
- Database connection pooling with PgBouncer
- Redis caching for frequently accessed data
- Async processing with RabbitMQ

## Security Considerations

- JWT tokens expire after 30 minutes
- Rate limiting prevents abuse
- Security headers (HSTS, XSS protection)
- Input validation with Pydantic
- SQL injection prevention via parameterized queries

## Monitoring and Logging

- Health check endpoint: /health
- Structured logging with log rotation
- Prometheus metrics at /metrics
- Cloud Monitoring alerts

## Backup Strategy

- Daily automated database backups
- GCS bucket for static file storage
- WORM Ledger for immutable audit records
