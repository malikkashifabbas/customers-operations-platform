# Postman — OpsPilot API

| File | What |
|---|---|
| `OpsPilot.postman_collection.json` | Every API, with headers, example bodies, response notes and security checks |
| `OpsPilot.local.postman_environment.json` | Local values: `baseUrl`, demo tenant / customer `public_id`s (from `seed_data`) |

**Use:** Postman → Import → both files → top-right environment = *OpsPilot Local* → run *Customers* or *Chat* requests.

| Variable | Meaning |
|---|---|
| `tenantId` | Demo Company |
| `otherTenantId` | NimbusTech (for the cross-tenant 401 check) |
| `customerId` | Ali Khan @ Demo Company (switch to `{{saraCustomerId}}` to chat as Sara) |
| `conversationId` | Chat memory key; filled automatically from the last chat response |
| `newCustomerPublicId` | Filled by *Create customer* |

The demo ids stay the same as long as the local database is not wiped; after `docker compose down -v` + `seed_data`, update them from `core_tenant` / `customers_customer`.

**Rule:** every new or changed API is added to the collection in the same change.
