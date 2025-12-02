# Product Availability & Pricing Normalization Service

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Setup](#setup)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Business Rules](#business-rules)
- [Assumptions](#assumptions)
- [Implementation Details](#implementation-details)
- [Monitoring](#monitoring)

## ✨ Features

### Core Features (Requirements 1-7)
- ✅ **Multi-Vendor Integration**: 3 vendors with different schemas
- ✅ **Data Normalization**: Unified product data format
- ✅ **Stock Normalization**: Smart handling of null/missing inventory
- ✅ **Price Validation**: Numeric validation with discard logic
- ✅ **Best Vendor Selection**: Lowest price + stock availability
- ✅ **Concurrent API Calls**: Parallel vendor queries using `asyncio.gather()`
- ✅ **Error Handling**: Graceful degradation on vendor failures
- ✅ **Redis Caching**: 2-minute TTL per SKU
- ✅ **Input Validation**: Alphanumeric SKU, 3-20 characters

### Senior Features (Requirements 8-15)
- ✅ **Third Vendor**: Simulated slow responses & intermittent failures
- ✅ **Data Freshness**: 10-minute timestamp validation
- ✅ **Price-Stock Decision Rule**: 10% price difference threshold
- ✅ **Request Timeouts**: 2-second timeout per vendor
- ✅ **Retry Logic**: 2 retry attempts with exponential backoff
- ✅ **Circuit Breaker**: 3 failures → 30s cooldown → half-open mode
- ✅ **Background Jobs**: Celery-based cache prewarming & performance logging
- ✅ **Rate Limiting**: 60 requests/minute per API key

### Bonus Features (Requirement 16)
- ✅ **OpenAPI/Swagger**: Auto-generated API docs at `/docs`
- ✅ **MVC Architecture**: Clean separation of concerns
- ✅ **Type Safety**: Full static typing with Pydantic
- ✅ **Documentation**: Inline comments & implementation guides

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Request                        │
│                    (x-api-key header)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Rate Limiter Middleware                    │
│              (60 requests/min per API key)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Router                          │
│                   (Input Validation)                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Product Controller                        │
│              (Request Orchestration)                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                     Product Service                          │
│         (Business Logic & Vendor Orchestration)              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ↓                     ↓
    ┌──────────────────┐   ┌──────────────────┐
    │  Redis Cache     │   │  Vendor Calls    │
    │  (2-min TTL)     │   │  (Concurrent)    │
    └──────────────────┘   └────────┬─────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ↓               ↓               ↓
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │  Circuit      │ │  Circuit      │ │  Circuit      │
            │  Breaker A    │ │  Breaker B    │ │  Breaker C    │
            └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                   │                │                │
                   ↓                ↓                ↓
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │  Retry Logic │ │  Retry Logic │ │  Retry Logic │
            │  (2 retries) │ │  (2 retries) │ │  (2 retries) │
            └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                   │                │                │
                   ↓                ↓                ↓
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │  Vendor A    │ │  Vendor B    │ │  Vendor C    │
            │  (JSON)      │ │  (JSON)      │ │  (JSON)      │
            └──────────────┘ └──────────────┘ └──────────────┘
                   │                │                │
                   └────────────────┴────────────────┘
                                    │
                                    ↓
                        ┌──────────────────────┐
                        │  Product Normalizer  │
                        │  (Data Transform)    │
                        └──────────┬───────────┘
                                   │
                                   ↓
                        ┌──────────────────────┐
                        │  Best Vendor Logic   │
                        │  (Price/Stock Rule)  │
                        └──────────┬───────────┘
                                   │
                                   ↓
                        ┌──────────────────────┐
                        │   Product View       │
                        │  (Response Format)   │
                        └──────────────────────┘
```

### Background Jobs (Celery)

```
┌─────────────────────────────────────────────────────────────┐
│                      Celery Beat                             │
│                  (Scheduler - Every 5 min)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      Redis Queue                             │
│                  (Message Broker)                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                     Celery Worker                            │
│                  (Task Executor)                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ↓                     ↓
    ┌──────────────────────┐  ┌──────────────────────┐
    │  Cache Prewarming    │  │  Vendor Performance  │
    │  (Top 10 SKUs)       │  │  Logging             │
    └──────────────────────┘  └──────────────────────┘
```

### MVC Pattern

```
app/
├── routers/          → Routes (Entry point)
├── controllers/      → Controllers (Request handling)
├── core/            → Core business logic
│   ├── service.py   → Service layer
│   ├── normalizer.py → Data transformation
│   ├── cache.py     → Redis cache manager
│   └── circuit_breaker.py → Circuit breaker
├── models/          → Data models (Pydantic)
├── views/           → Response formatting
├── middleware/      → Request middleware
├── data/            → Vendor data sources
└── tasks/           → Background jobs (Celery)
```

## 🚀 Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd stock-and-price-validator
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Redis

**macOS (Homebrew):**
```bash
brew install redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
```

### 5. Environment Configuration (Optional)
```bash
cp .env.example .env
# Edit .env if needed (defaults work for local development)
```

## 🎯 Running the Application

### Option 1: Manual Start (Development)

**Terminal 1: Start Redis**
```bash
redis-server
```

**Terminal 2: Start FastAPI Application**
```bash
uvicorn app.main:app --reload --port 8000
```

**Terminal 3: Start Celery (Background Jobs)**
```bash
./start_celery.sh
```

### Option 2: Docker Compose (Production-like)
```bash
docker-compose up -d
```

### Verify Installation
```bash
# Check health endpoint
curl http://localhost:8000/health

# Test with API key
curl -H "x-api-key: test-key-123" http://localhost:8000/products/SKU001
```

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints

#### 1. Get Product
```http
GET /products/{sku}
```

**Headers:**
```
x-api-key: your-api-key-here
```

**Response (200 OK):**
```json
{
  "sku": "SKU001",
  "vendor": "VendorB",
  "price": 95.5,
  "stock": 20,
  "status": "AVAILABLE",
  "timestamp": "2025-12-02T18:27:01.587845"
}
```

**Response (OUT_OF_STOCK):**
```json
{
  "sku": "SKU999",
  "vendor": null,
  "price": null,
  "stock": null,
  "status": "OUT_OF_STOCK",
  "timestamp": "2025-12-02T18:27:01.587845"
}
```

**Error Responses:**

**401 Unauthorized** (Missing API Key):
```json
{
  "error": "Missing API Key",
  "detail": "x-api-key header is required",
  "timestamp": "2025-12-02T18:27:01.587845"
}
```

**429 Too Many Requests** (Rate Limit Exceeded):
```json
{
  "error": "Rate Limit Exceeded",
  "detail": "Maximum 60 requests per minute allowed",
  "current_count": 61,
  "limit": 60,
  "retry_after": 60,
  "timestamp": "2025-12-02T18:27:01.587845"
}
```

**400 Bad Request** (Invalid SKU):
```json
{
  "error": "Invalid SKU format",
  "detail": "SKU must be alphanumeric and 3-20 characters long",
  "received": "SK@1"
}
```

#### 2. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "product-normalization-service"
}
```

#### 3. Root
```http
GET /
```

**Response:**
```json
{
  "service": "Product Availability & Pricing Normalization Service",
  "version": "1.0.0",
  "endpoints": {
    "get_product": "/products/{sku}",
    "docs": "/docs"
  }
}
```

## 🧪 Testing

### Rate Limiter Tests

**Bash Script (Quick):**
```bash
./test_rate_limit.sh
```

**Python Script (Detailed Metrics):**
```bash
python test_rate_limit.py
```

See [RATE_LIMITER_TESTING.md](RATE_LIMITER_TESTING.md) for details.

### Manual Testing

**Test 1: Valid Request**
```bash
curl -H "x-api-key: test-key-123" http://localhost:8000/products/SKU001
```

**Test 2: Invalid SKU**
```bash
curl -H "x-api-key: test-key-123" http://localhost:8000/products/SK@1
```

**Test 3: No API Key**
```bash
curl http://localhost:8000/products/SKU001
```

**Test 4: Rate Limiting**
```bash
# Make 65 requests rapidly
for i in {1..65}; do
  curl -H "x-api-key: test-key-123" http://localhost:8000/products/SKU001
  sleep 0.1
done
```

## 📁 Project Structure

```
stock-and-price-validator/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry
│   ├── controllers/               # Request handlers
│   │   ├── __init__.py
│   │   └── product_controller.py
│   ├── core/                      # Business logic
│   │   ├── cache.py              # Redis cache manager
│   │   ├── circuit_breaker.py    # Circuit breaker pattern
│   │   ├── normalizer.py         # Data normalization
│   │   └── service.py            # Product service
│   ├── data/                      # Data sources
│   │   ├── vendor_a_products.json
│   │   ├── vendor_b_products.json
│   │   ├── vendor_c_products.json
│   │   └── vendors.py            # Vendor implementations
│   ├── middleware/                # Request middleware
│   │   └── rate_limiter.py       # Rate limiting
│   ├── models/                    # Data models
│   │   └── models.py             # Pydantic models
│   ├── routers/                   # API routes
│   │   ├── __init__.py
│   │   └── products.py
│   ├── tasks/                     # Background jobs
│   │   ├── __init__.py
│   │   ├── celery_app.py         # Celery configuration
│   │   ├── jobs.py               # Job manager
│   │   └── scheduled.py          # Scheduled tasks
│   └── views/                     # Response formatting
│       ├── __init__.py
│       └── product_view.py
├── logs/                          # Application logs
│   ├── celery_worker.log
│   └── celery_beat.log
├── .env.example                   # Environment template
├── .gitignore
├── docker-compose.yml             # Docker configuration
├── requirements.txt               # Python dependencies
├── readme.md                      # This file
├── start_celery.sh               # Start Celery services
├── stop_celery.sh                # Stop Celery services
├── test_rate_limit.sh            # Rate limiter test (bash)
├── test_rate_limit.py            # Rate limiter test (python)
└── Documentation/
    ├── BACKGROUND_JOB_IMPLEMENTATION.md
    ├── CELERY_IMPLEMENTATION.md
    ├── CIRCUIT_BREAKER_IMPLEMENTATION.md
    ├── DATA_FRESHNESS_IMPLEMENTATION.md
    ├── PRICE_STOCK_RULE_IMPLEMENTATION.md
    ├── RATE_LIMITER_TESTING.md
    ├── RATE_LIMITING_IMPLEMENTATION.md
    ├── TIMEOUT_RETRY_CACHE_IMPLEMENTATION.md
    └── VENDOR_C_IMPLEMENTATION.md
```

## 📖 Business Rules

### 1. Stock Normalization
```python
if inventory == null and status == "IN_STOCK":
    stock = 5  # Assume stock available
else:
    stock = 0  # Out of stock
```

### 2. Price Validation
- Must be numeric
- Must be > 0
- Invalid entries are discarded

### 3. Best Vendor Selection

**Rule 1: Price Difference ≤ 10%**
```python
if (max_price - min_price) / min_price <= 0.10:
    select vendor with lowest price
```

**Rule 2: Price Difference > 10%**
```python
if (max_price - min_price) / min_price > 0.10:
    select vendor with highest stock
```

### 4. Data Freshness
```python
if timestamp < (current_time - 10 minutes):
    discard data  # Stale data
```

### 5. Circuit Breaker States
```
CLOSED → (3 failures) → OPEN → (30s cooldown) → HALF_OPEN → (1 success) → CLOSED
                                                      ↓ (failure)
                                                     OPEN
```

## 💡 Assumptions

### 1. Vendor Data Sources
**Assumption**: Vendors are simulated using JSON files instead of real HTTP APIs.

**Rationale**: 
- Easier to test and demonstrate
- No external dependencies
- Consistent behavior for evaluation
- Can simulate various scenarios (slow responses, failures)

**Implementation**: Mock vendors in `app/data/vendors.py` with simulated delays and failures.

---

### 2. API Key Authentication
**Assumption**: Simple API key validation without database lookup.

**Rationale**:
- Focus on rate limiting logic
- Production would use proper auth (JWT, OAuth2)
- Sufficient for demonstration purposes

**Implementation**: Any non-empty `x-api-key` header is accepted.

---

### 3. Stock Assumption (null + IN_STOCK)
**Assumption**: If `inventory = null` but `status = "IN_STOCK"`, assume `stock = 5`.

**Rationale**:
- Vendor may not expose exact inventory counts
- "IN_STOCK" indicates availability
- Conservative estimate (5 units) balances availability vs overselling
- Requirement explicitly states this rule

**Implementation**: Applied in `ProductNormalizer` for all vendors.

---

### 4. Timestamp Format Standardization
**Assumption**: All vendors now use ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`).

**Rationale**:
- Originally Vendor B used Unix timestamps
- Standardized for consistency and easier parsing
- ISO 8601 is industry standard
- Simplifies datetime comparisons

**Implementation**: All JSON files use `updated_at` or `last_updated` with ISO strings.

---

### 5. Cache Key Strategy
**Assumption**: Cache key is `product:{sku}` (simple SKU-based).

**Rationale**:
- SKU uniquely identifies products
- No need for vendor-specific caching
- Best vendor is already selected before caching
- Simpler cache invalidation

**Implementation**: `cache.get_cache_key("product", sku)` in `ProductService`.

---

### 6. Concurrent Vendor Calls
**Assumption**: All vendor calls happen in parallel, even if one fails.

**Rationale**:
- Requirement specifies `asyncio.gather()`
- Faster response times
- Graceful degradation (use available vendors)
- Circuit breaker prevents wasted calls to failing vendors

**Implementation**: `asyncio.gather()` with `return_exceptions=False`.

---

### 7. Background Job Frequency
**Assumption**: Background jobs run every 5 minutes (fixed schedule).

**Rationale**:
- Requirement specifies 5-minute interval
- Balance between freshness and load
- Sufficient for cache prewarming
- Celery Beat handles scheduling

**Implementation**: Celery Beat schedule with 300-second interval.

---

### 8. Rate Limit Window
**Assumption**: Rate limit window is per-minute (sliding window).

**Rationale**:
- Requirement specifies "60 requests per minute"
- Sliding window is more accurate than fixed window
- Redis key includes current minute
- Automatic expiration via TTL

**Implementation**: Redis key format `rate_limit:{api_key}:{YYYY-MM-DD-HH-MM}`.

---

### 9. Vendor C Failure Simulation
**Assumption**: Vendor C fails ~30% of the time randomly.

**Rationale**:
- Demonstrates circuit breaker functionality
- Simulates real-world unreliable vendors
- Shows graceful degradation
- Requirement asks for "intermittent failures"

**Implementation**: `random.random() < 0.3` in `VendorC.get_product()`.

---

### 10. Error Response Format
**Assumption**: Errors return JSON with `error`, `detail`, and `timestamp` fields.

**Rationale**:
- Consistent error format
- Machine-readable
- Includes context for debugging
- Follows REST best practices

**Implementation**: Custom error responses in controllers and middleware.

## 🔧 Implementation Details

### Key Technologies
- **FastAPI**: Modern async web framework
- **Pydantic**: Data validation and serialization
- **Redis**: Caching and rate limiting
- **Celery**: Background job processing
- **asyncio**: Concurrent vendor calls

### Design Patterns
- **MVC Architecture**: Separation of concerns
- **Circuit Breaker**: Fault tolerance
- **Retry Pattern**: Transient failure handling
- **Repository Pattern**: Data access abstraction
- **Middleware Pattern**: Cross-cutting concerns

### Performance Optimizations
- Concurrent vendor API calls
- Redis caching (2-minute TTL)
- Circuit breaker (skip failing vendors)
- Connection pooling (Redis)
- Async I/O throughout

## 📊 Monitoring

### Logs
- **Application**: Console output
- **Celery Worker**: `logs/celery_worker.log`
- **Celery Beat**: `logs/celery_beat.log`

### Metrics (Available in Logs)
- Request count per SKU
- Vendor response times
- Vendor failure rates
- Circuit breaker states
- Cache hit/miss rates

### Celery Monitoring (Flower)
```bash
pip install flower
celery -A app.tasks.celery_app flower --port=5555
```
Access at: http://localhost:5555

