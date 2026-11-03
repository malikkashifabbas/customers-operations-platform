# Postman — OpsPilot API

| File | What |
|---|---|
| `OpsPilot.postman_collection.json` | Every API, with auth, example bodies, response notes and security checks |
| `OpsPilot.local.postman_environment.json` | Local values: `baseUrl`, demo `tenant_public_id`s, phones and staff username (from `seed_data`) |

**Use:** Postman → Import → both files → top-right environment = *OpsPilot Local* → put `DEMO_PASSWORD` from your `.env` into `demoPassword` → run *Auth → Customer login (Ali)* and *Auth → Staff login*.

**New customer with their own password:** *Auth → Customer signup*. Staff can also create one with a `password` in *Customers → Create customer*, and reset it with *Reset customer password*. Changing or resetting a password ends all old sessions: log in again.

| Variable | Meaning |
|---|---|
| `tenantPublicId` | Demo Company — `core_tenant.public_id`, sent in the customer login body |
| `otherTenantPublicId` | NimbusTech |
| `customerPhone` / `saraPhone` | Demo customers' phones for login |
| `staffUsername` | `staff.demo-company` |
| `demoPassword` | **Secret, empty in git** — `DEMO_PASSWORD` from your `.env` |
| `accessToken` / `refreshToken` | Filled by a customer login; used by *Chat*, *Tickets*, *Guardrails* |
| `staffAccessToken` | Filled by *Staff login*; used by *Customers* and *Staff approvals* |
| `conversationId` | Chat memory key; filled automatically from the last chat response |
| `newCustomerPublicId` | Filled by *Create customer* |
| `ticketPublicId` | Filled by *Create ticket*; *Get ticket* polls it until `answered` (needs relay + worker running) |

Access tokens last 15 minutes: on a 401 run *Refresh access token* or log in again. After `docker compose down -v` + `seed_data`, get the new ids with `uv run src/manage.py list_ids`.

**Guardrails folder:** each request checks `blocked_reason` in a Postman test (Tests tab). Chat responses now also carry `blocked_reason` and `output_flags`; SSE streams can send `guardrail` and `replace` events.

**Staff approvals folder (Lesson 13):** refund tickets pause with status `waiting_approval`; approve/reject here and the worker resumes the agent. *List* fills `ticketPublicId` with the oldest waiting ticket. The reviewer comes from the staff token.

**Agent writes (Lesson 18):** *Chat → Ask agent to open a ticket* pauses with `confirmation_required`; *Confirm pending action* or *Cancel pending action* decides. Only this API can approve, a chat message cannot.

**Name and email (Lesson 18B):** *Ask agent to change my name* or *my email*, then *Confirm pending action*. The email link prints in the runserver terminal: copy its token into `emailChangeToken` and run *Auth → Open email confirmation link*. Demo Company only.

**Rule:** every new or changed API is added to the collection in the same change.
