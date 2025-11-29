Note: This is a assignment.

Title: Product Availability & Pricing Normalization Service

Objective:
Integrate with two external vendor APIs, normalize inconsistent product data, apply business
rules, and return the best vendor.

Requirements
1. Vendor Integrations (2 Vendors)
● Each vendor must have different field names, data types, and structures.
● Candidates may simulate these vendors using mock endpoints or JSON files.
2. API Endpoint
GET /products/{sku}
3. Business Logic
● Stock Normalization
○ If vendor returns:
■ inventory = null AND status ="IN_STOCK" → assume stock = 5
■ Otherwise → stock = 0

● Price Validation
○ Price must be numeric and > 0
○ Invalid entries must be discarded
● Best Vendor Selection
○ Vendor with stock > 0 and lowest price wins
○ If both out of stock → return OUT_OF_STOCK

4. Concurrency
● Call both vendors in parallel
○ Promise.all() in NestJS
○ asyncio.gather() in FastAPI

5. Error Handling
● If one vendor fails or times out, skip gracefully and return what’s available.

6. Caching (Required)
● In-memory or Redis
● TTL = 60 seconds
● Cache per SKU

7. Validation
● SKU must be alphanumeric
● Length: 3–20 characters

Senior candidates must complete all core requirements above plus the following
enhancements.
8. Add a Third Vendor
● This vendor must simulate:
○ Slow responses
○ Intermittent failures
○ Different field structure
● Must be queried concurrently with others
9. Data Freshness Rule
● Vendors will return a timestamp.
● Ignore (discard) vendor data older than 10 minutes.
10. Price–Stock Decision Rule Upgrade
● If vendors differ in price by more than 10%,
→ choose the vendor with higher stock, even if the price is slightly higher.
11. Request Timeouts & Retries
● Apply a vendor API timeout (e.g., 2 seconds)
● Implement retry logic with limited attempts (e.g., 2 retries)
12. Mandatory Redis Cache
● Senior version must use Redis (not in-memory)
● TTL = 2 minutes

13. Circuit Breaker (for the failing vendor)
● Open after 3 consecutive failures
● Skip vendor calls for 30 seconds while open
● After cooldown, enter half-open mode
● One successful call closes the circuit
14. Background Job
Every 5 minutes, run a scheduled task:
● Prewarm cache for most-frequently-requested SKUs
● Log vendor performance (latency + failures)
15. Rate Limiting
Implement simple rate limiting:
● 60 requests per minute per API key (x-api-key)

16. Optional Bonus (For Both Senior & Junior Roles)
● Docker Compose (API + Redis)
● Swagger/OpenAPI
● Unit / integration tests

Note:
- Junior Candidates are only required to fulfill the requirement of Junior Anything
additional is bonus point
- Anything not available in the information make an assumption, Explain why you
assumed that in your code as comment
- Language & Framework: Python (FastAPI), Node.JS (NestJS)
- All code should be static typed even for python
- All code should be documented