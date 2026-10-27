# Postman — OpsPilot API

| File | What |
|---|---|
| `OpsPilot.postman_collection.json` | Every API, with headers, example bodies, response notes and security checks |
| `OpsPilot.local.postman_environment.json` | Local values: `baseUrl`, demo tenant / customer `public_id`s (from `seed_data`) |

**Use:** Postman → Import → both files → top-right environment = *OpsPilot Local* → run *Customers* or *Chat* requests.

| Variable | Meaning |
|---|---|
| `tenantPublicId` | Demo Company — `core_tenant.public_id`, sent as `X-Tenant-Public-Id` |
| `otherTenantPublicId` | NimbusTech (for the cross-tenant 401 check) |
| `customerPublicId` | Ali Khan @ Demo Company — `customers_customer.public_id`, sent as `X-Customer-Public-Id` (switch to `{{saraCustomerPublicId}}` to chat as Sara) |
| `conversationId` | Chat memory key; filled automatically from the last chat response |
| `newCustomerPublicId` | Filled by *Create customer* |
| `ticketPublicId` | Filled by *Create ticket*; *Get ticket* polls it until `answered` (needs relay + worker running) |

The demo ids stay the same as long as the local database is not wiped; after `docker compose down -v` + `seed_data`, get the new ones with `uv run src/manage.py list_ids`.

**Guardrails folder:** each request checks `blocked_reason` in a Postman test (Tests tab). Chat responses now also carry `blocked_reason` and `output_flags`; SSE streams can send `guardrail` and `replace` events.

**Rule:** every new or changed API is added to the collection in the same change.
