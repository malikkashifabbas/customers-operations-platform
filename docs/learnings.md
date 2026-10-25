# OpsPilot — Meri Learnings

Har nayi cheez jo is project mein seekhi, yahan ek "Learning" ban kar likhi jati hai: kya hai, kyun zaroori hai, aur kaise check karein.

---

## Learning 1: Har repo ki apni Git identity

**Date:** 23 Oct 2026 · **Lesson:** 2 (Step 2.1)

### Kya hai?
Har git commit par ek **naam** aur **email** likha jata hai (author). GitHub isi email se commit ko aapke GitHub account se jorta hai.
- `pyproject.toml` ka `authors` sirf project ki maloomat hai — **commits par uska koi asar nahi**.
- Commit kis naam se hoga, ye `git config` decide karta hai.

### Do levels: global vs local
| Level | Command | Kahan save hota hai | Kis par lagta hai |
|---|---|---|---|
| **Global** | `git config --global user.email "..."` | `C:\Users\<user>\.gitconfig` | Computer ke **saare** repos |
| **Local** | `git config user.email "..."` (bina `--global`) | Repo ki `.git/config` | **Sirf yahi** repo |

Local, global se jeet jata hai. Isi liye office ke repos purani identity par rehte hain aur OpsPilot nayi identity par.

### Is project mein kya kiya
```bash
git config user.name "Malik Kashif Abbas"
git config user.email "malikkashifabbas28@gmail.com"
```

### Kaise check karein — is repo mein kaun si identity aur kaun sa GitHub juda hai
```bash
git config user.name                    # commits kis naam se honge
git config user.email                   # commits kis email se honge
git config --show-origin user.email     # ye value KIS FILE se aa rahi hai (local ya global)
git config --list --local               # sirf is repo ki saari settings
git remote -v                           # ye repo kis GitHub/remote repo se juda hai (khali = abhi kisi se nahi)
git log --format="%h %an <%ae>" -5      # pichle 5 commits kis naam/email se hue
```

### Yaad rakhne wali baatein
- Pehle commit se **pehle** identity check karein — baad mein purane commits ka author badalna mushkil hai.
- Jo email commits mein hai, wo GitHub account ki **Settings → Emails** mein added honi chahiye, warna commit aapki profile par nahi dikhega.
- `git remote -v` khali hai to repo abhi sirf aapke computer par hai; GitHub par push ke liye pehle `git remote add origin <url>` karna hoga.

---

## Learning 2: Settings ko base / dev / prod mein baantna

**Date:** 23 Oct 2026 · **Lesson:** 2B

### Kya hai?
Ek `settings.py` ki jagah ek **package** `src/config/settings/`:
| File | Kis ke liye | Khaas baat |
|---|---|---|
| `base.py` | Sab ki common settings | `DEBUG = False` — base hamesha **mehfooz** default |
| `dev.py` | Apna computer | `from .base import *` phir `DEBUG = True`, dev secret key |
| `prod.py` | Asal server | Secret key + hosts **environment variables** se, secure cookies |

### Teen cheezein jo seekhi
1. **`BASE_DIR` mein teesra `.parent`** — file ek folder neeche gayi (`settings/base.py`), to `src/` tak pahunchne ke liye ek `.parent` aur. Bhoole to DB file ghalat jagah banti hai. Sab se aam galti.
2. **Fail fast** — `os.environ["X"]` (square brackets) variable na mile to server **foran crash** (`KeyError`). `.get("X")` khamoshi se khali value de deta aur server ghalat chalta rehta.
3. **`setdefault`** — `manage.py` default `config.settings.dev`, `asgi.py`/`wsgi.py` default `config.settings.prod`; server par `DJANGO_SETTINGS_MODULE` env set ho to wahi jeetta hai.

### Kaise check karein
```bash
uv run src/manage.py diffsettings          # kaun si settings load hui (SETTINGS_MODULE, DEBUG, BASE_DIR)
uv run src/manage.py check --deploy        # production security checklist (prod settings ke saath)
```
PowerShell mein prod try karna:
```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.prod"   # is terminal mein prod settings
Remove-Item Env:DJANGO_SETTINGS_MODULE                 # wapas dev
```

### `check --deploy` ki 3 warnings (deploy wale lesson mein theek hongi)
- **W004 HSTS** — browser ko batana ke site hamesha HTTPS par khole.
- **W008 SSL redirect** — HTTP request ko HTTPS par bhejna (ya load balancer kare).
- **W009 SECRET_KEY** — kam az kam 50 random characters, `django-insecure-` wali nahi.

---

## Learning 3: Docker Compose — Postgres, Redis, Kafka ek file se

**Date:** 23 Oct 2026 · **Lesson:** 3A

### `docker-compose.yml` kya hai (aur kya nahi)
- Ek **recipe** jo batati hai: kaun se containers, kaun si image + version, kaun se ports, kaun se env variables, data kahan (volumes), aur "zinda ho?" (healthcheck).
- Postgres/Redis/Kafka ki **sirf wo settings** jo env variables ya `command` se di jati hain. Har cheez nahi — Postgres ka andar ka tuning (`postgresql.conf`), Kafka ke topics, Redis ka data — ye sab apni jagah rehte hain.
- **Docker khud ki settings** (memory, CPU, disk) Docker Desktop ki Settings mein hain, is file mein nahi.
- Ek command `docker compose up -d` se poori team ka bilkul **same** setup — "mere computer par to chalta tha" khatam.

**Is file mein NAHI hota:**
| Cheez | Kahan hoti hai |
|---|---|
| Docker ki apni settings (RAM, CPU, disk) | Docker Desktop → Settings |
| Postgres ki andar ki tuning (memory, connections) | `postgresql.conf` (zaroorat ho to mount) |
| Database ki tables | Django migrations |
| Kafka ke topics | Code (`infra/eventbus/topics.py`) ya CLI |
| Redis ka data / keys | Redis ke andar, app likhti hai |
| Production setup | Kubernetes/ECS, ya managed services (AWS RDS, ElastiCache, MSK, Confluent Cloud) |

Compose file **local development** ke liye hai; production mein Postgres/Redis/Kafka aksar managed services hoti hain (backup, update, scaling cloud company karti hai).

### ⚠️ `POSTGRES_PASSWORD` sirf PEHLI dafa kaam karta hai
Postgres image user/password **sirf tab** banati hai jab volume khali ho (pehla `up`). Baad mein `.env` ka password badla → database ka password **nahi** badla → "password authentication failed".
Mere saath hua: pehla `up` ek password se hua, baad mein `.env` mein naya password likha, Beekeeper fail.
Do hal:
```bash
# 1) Database ke andar password badlo (data bacha rehta hai)
docker compose exec postgres psql -U opspilot -d opspilot -c "ALTER USER opspilot WITH PASSWORD '<naya-password>';"
# 2) Ya sab mita kar naye sire se (⚠️ saara DB data khatam) — sirf jab DB khali/bekaar ho
docker compose down -v
docker compose up -d
```
`.env` mein `#` wala password **quotes** mein rakho (`'abc#123'`), warna `#` ke baad wala hissa comment ban sakta hai. Database URL mein `#` ko `%23` likhna parta hai.

**Kaun sa password sach mein laga hai — check (Docker network se, asli password check ke saath):**
```bash
docker run --rm --network opspilot_default -e PGPASSWORD=<password> pgvector/pgvector:0.8.7-pg17 psql -h postgres -U opspilot -d opspilot -c "SELECT 1"
```
(`docker compose exec postgres psql -h 127.0.0.1 ...` se test mat karna — container ke andar se 127.0.0.1 "trust" hai, ghalat password bhi pass ho jata hai.)

### Ports: `"HOST:CONTAINER"`
`"5433:5432"` = Windows ka 5433 → container ka 5432. Ek port par ek hi program — mere Windows par pehle se native Postgres **5432** par tha, isliye Docker wala **5433**.

**Beekeeper / DBeaver se Docker Postgres:** Host `localhost`, Port **5433**, User `opspilot`, DB `opspilot`, password `.env` wala. Port 5432 likha to native Windows Postgres milega (uska user `postgres` hai) → "password authentication failed for user opspilot".

### Kafka ke "do darwaze" (listeners)
| Kaun connect kar raha hai | Pata |
|---|---|
| Docker network ke andar ka container (Kafka UI, baad mein workers) | `kafka:19092` |
| Windows par chalne wali app (Django, `uv run`) | `localhost:9092` |
Container ke andar `localhost` = **wahi container**, Windows nahi.

### Redis = temporary memory
```bash
docker compose exec redis redis-cli SET lesson3 "hello" EX 60   # 60 second ki zindagi
docker compose exec redis redis-cli TTL lesson3                 # kitne second baqi (Time To Live)
```

### Is lesson mein khud dekha
- **Bina key ke 5 messages → sab partition 2 mein.** Producer key na de to "sticky partitioner" ek batch ek hi partition mein daal deta hai. Key do (`ticket_id`) to `hash(key)` se partition tay hota hai — isi liye OpsPilot mein key lazmi.
- **Ghalat topic (`lesson3.typo`) par bheja → `UNKNOWN_TOPIC_OR_PARTITION`**, topic bana hi nahi. `AUTO_CREATE_TOPICS_ENABLE=false` ne typo pakar liya.
- **Redis key 60 second baad `TTL = -2`** — matlab key khud mit chuki (`-1` = key hai magar expiry nahi).

### Roz ki commands
```bash
docker compose up -d          # sab chalao (background)
docker compose ps             # haal + (healthy)
docker compose logs -f kafka  # ek service ke logs live
docker compose stop           # rok do, data safe
docker compose down           # containers hatao, volumes safe
docker compose down -v        # ⚠️ volumes bhi — saara DB data khatam
```
`restart: unless-stopped` — computer restart par containers khud chal jate hain, jab tak khud `stop` na kiya ho.

### Har service ki roz ki dekh-bhaal
| | Kya dekhte hain | Kaise |
|---|---|---|
| **Postgres** | Tables, data, slow queries | Beekeeper (5433), `psql`, Django admin. Schema sirf **migrations** se |
| **Redis** | Keys, TTL, memory | `redis-cli`: `SCAN 0 MATCH opspilot:*`, `TTL key`, `INFO memory` (visual: Redis Insight). Har key par TTL ho |
| **Kafka** | Topics, messages, **consumer lag** | Kafka UI (8080). Lag = kitne messages abhi process nahi hue; barhta jaye to workers peeche hain |

**Production mein:** monitoring (Grafana), Postgres ke automatic backups (asal sach Postgres mein; Redis/Kafka "rebuild ho sakne wala" data), topics code review ke baad, versions pinned aur upgrade test karke.

### Grafana kya hai?
Open-source **dashboard tool** — gaari ke dashboard (speed, petrol, temperature) jaisa, magar system ke liye.
- Khud data jama nahi karta; **data sources** se parhta hai: **Prometheus** (numbers/metrics jama karne wala time-series database), Loki (logs), Postgres waghera.
- Har service ka ek **exporter** uske numbers Prometheus ko deta hai: `postgres_exporter`, `redis_exporter`, `kafka-exporter`; Django/workers apne metrics khud dete hain.
- **Alerts:** "consumer lag 5 minute se 1000 se upar" → Slack/email/phone.
- OpsPilot ka dashboard: tickets/minute, LLM response time, LLM cost/din, Kafka consumer lag, Postgres connections, Redis memory.
- Hum isay observability wale lesson mein `docker-compose.yml` mein add karenge (Prometheus + Grafana).

---

## Learning 4: Django → Docker Postgres, `.env` se settings, pehli `migrate`

**Date:** 23 Oct 2026 · **Lesson:** 3B

### Raasta
```
.env ──► src/config/env.py (pydantic-settings: parho + type check) ──► settings/base.py DATABASES ──► psycopg ──► Postgres (localhost:5433)
```
Ek hi `.env` se Docker bhi password leta hai aur Django bhi — dono kabhi alag nahi honge.

### Nayi libraries
| Library | Kaam |
|---|---|
| `psycopg[binary]` (v3) | Python ↔ Postgres **driver**. `[binary]` = tayyar compiled (Windows par compiler nahi chahiye). LangGraph ka Postgres checkpointer bhi yahi use karta hai. `psycopg2` purana hai |
| `pydantic-settings` | Env variables + `.env` parhta hai **aur type check** karta hai; zaroori variable na mile to start par hi `ValidationError` (fail fast) |

### `env.py` ki khaas baatein
- Field `postgres_db` ↔ env `POSTGRES_DB` (chhote/bare huroof ka farq nahi).
- Default ho (`postgres_port: int = 5433`) to optional, warna **zaroori**. `: int` → `"5433"` khud number, `"abc"` par error.
- **Asal environment variable `.env` se jeet jata hai** — production mein `.env` hoti hi nahi.
- `SecretStr` → print/log par `**********`; asal value sirf `.get_secret_value()` se, sirf `DATABASES` mein.
- Alag `HOST/PORT/USER/PASSWORD` variables, ek `DATABASE_URL` nahi — URL mein `#`, `@`, `/` wale password toot-te hain.
- `DATABASES` **`base.py`** mein: dev/prod dono Postgres; sirf values alag, jo env se aati hain.

### Migrations
- **Migration** = database ki shakal (tables/columns) badalne wali Python file; database ke dhaanche ki "git history".
- `django_migrations` table = kaun si migration kab lagi. Django isi se jaanta hai kya baqi hai.
- Pehli `migrate` ne 18 migrations lagayin → 10 tables (`auth_*`, `django_*`).

### Commands
```bash
uv run src/manage.py check --database default   # sach mein DB se connect karke check
uv run src/manage.py showmigrations             # [ ] baqi, [X] lag chuki
uv run src/manage.py migrate                    # baqi migrations lagao
uv run src/manage.py createsuperuser            # admin user (password khud type karo)
```

### Is lesson mein khud dekha
- `uv add` ke dauraan chalta hua `runserver` crash hua: `ModuleNotFoundError: No module named 'pydantic'` — code ne nayi library import kar li thi magar install abhi poora nahi hua tha. Install ke baad dobara chalaya → theek.
- Migrate ke baad "You have 18 unapplied migrations" wali warning khatam.
- Admin login pehle fail: `createsuperuser` terminal mein username ke sawal par **ruki** hui thi, user bana hi nahi tha (`auth_user` khali). Sawalon ke jawab diye → user bana → login ho gaya.

### Password database mein kaise save hota hai
`auth_user.password` = `algorithm$iterations$salt$hash`, maslan `pbkdf2_sha256$1000000$<22 huroof salt>$<44 huroof hash>`.
- **Hash** = ek-tarfa hisaab: password se hash ban sakta hai, hash se password wapas **nahi**. Login par Django naye type kiye password ka hash bana kar milata hai.
- **Salt** = har user ka alag random tukda, taa ke do users ka same password ho to bhi hash alag ho (tayyar "rainbow tables" bekaar).
- **1,000,000 iterations** = hash 10 lakh dafa dohraya jata hai — login par ek pal, magar chori hua database "brute force" karne wale ke liye bohat mehenga.

---

## Learning 5 ⭐: Tenant, BaseModel, `id` vs `public_id` — OpsPilot ki bunyaad

**Date:** 23 Oct 2026 · **Lesson:** 4 · **Files:** `src/core/models/base.py`, `tenant.py`, `__init__.py`, `src/core/admin.py`

> Ye project ka **sab se zaroori** usool hai. Har naya model banate waqt ye page dobara parho.

### 1. Tenant kya hai aur itna zaroori kyun?
OpsPilot ek **SaaS** (Software as a Service) hai: **ek system, ek database, kai companies**. Har company (client) ek **tenant** hai — jaise ek building, kai kirayedar, har ek ka apna taala.

```
OpsPilot (ek database)
├── Tenant 1: "Hypernim"      → iske customers, tickets, invoices
├── Tenant 2: "NimbusTech"    → iske customers, tickets, invoices
└── Tenant 3: "Demo Company"  → ...
```

**Kyun zaroori:** ek company **kabhi bhi** doosri company ka data na dekh sake, na badal sake, na utha sake. Isliye:
- **Har table ki har row** par `tenant_id` hoga.
- **Har query** `WHERE tenant_id = <current tenant>` ke saath chalegi — API ho, admin ho, ya AI agent ka tool.
- **Har Kafka event** mein `tenant_id`; LangGraph `thread_id = "tenant:ticket"`; Store namespace `(tenant, "customers", id)`.
- Ek bhi query tenant filter bhool gayi = ek company ka data doosri ko — sab se bara security haadsa. Isliye har app mein `test_tenant_isolation.py` hoga.
- `tenant_id` **pehle din se** — baad mein lakhon rows wali tables mein add karna taqreeban naamumkin.
- Pehle dekha hua: MyCRMSim ka `workspace_id` / AI service ka `X-Workspace-ID` header = yahi tenant.

`Tenant` model (`core_tenant` table): `name`, `slug` (URL-safe, unique: `demo-company`), `is_active` (account band karna ho to delete nahi, `False` — soft disable).

### 2. BaseModel kyun? (abstract model)
Invoice, Ticket, Customer, Order… **alag cheezein**, magar har ek ko **same cheezein** chahiye: `public_id`, `created_at`, `updated_at` — aur har ek kisi **tenant** ka hai. Har model mein ye baar baar likhna = copy-paste + bhoolne ka khatra.

**Hal: abstract model** — khud **table nahi banata**, sirf apne fields wirasat (inheritance) mein deta hai:
```
BaseModel (abstract)               → public_id, created_at, updated_at   (+ id Django khud)
 ├── Tenant (asal table)            → + name, slug, is_active
 └── TenantScopedModel (abstract)   → + tenant  (ForeignKey → core.Tenant)
       ├── Customer  (aage)
       ├── Invoice   (aage)
       └── Ticket    (aage)  ← har ek ko tenant khud mil jayega
```
Naya model = `class Invoice(TenantScopedModel): ...` — tenant bhoolna **mumkin hi nahi**.
Saboot: 3 classes likhi, `makemigrations` ne sirf **1 table** (`core_tenant`) banayi — abstract ki table nahi banti (`class Meta: abstract = True`).

### 3. `id` aur `public_id` — dono kyun?
| | `id` (BigInt: 1, 2, 3…) | `public_id` (UUID: `ac5b565b-f62b-4806-…`) |
|---|---|---|
| Kahan | **Database ke andar** — joins, foreign keys (`tenant_id`) | **Bahar** — API URLs, Kafka events, frontend, logs jo client dekhe |
| Kyun | Chhota (8 bytes), tez, index halka | Andaza lagana naamumkin |
| Khatra agar bahar diya | `/tickets/5` → koi `/tickets/6` try kare (**enumeration attack**), aur kitne tickets hain wo bhi pata chal jaye | — |

**UUID** = Universally Unique Identifier. `id` Django khud banata hai (`DEFAULT_AUTO_FIELD = BigAutoField`), isliye model mein likha hi nahi.

### Har field ki khaas baat
| Code | Matlab / gotcha |
|---|---|
| `default=uuid.uuid4` (**bina bracket**) | Function khud diya, taa ke har row par naya UUID. `uuid.uuid4()` likhte to ek hi UUID **har row** ko milta |
| `unique=True` | Postgres khud unique index banata hai (tez dhoondna) |
| `editable=False` | Admin/forms mein badla nahi ja sakta |
| `auto_now_add=True` | Sirf banate waqt waqt likho |
| `auto_now=True` | Har `.save()` par naya waqt. ⚠️ `queryset.update()` par **nahi** badalta — khud `updated_at=timezone.now()` do |
| `ForeignKey("core.Tenant", ...)` | Text mein naam → circular import nahi. Postgres `tenant_id` par khud index banata hai |
| `on_delete=models.PROTECT` | Jab tak tenant ka data hai, tenant **delete nahi** ho sakta. `CASCADE` = tenant mita to saara data bhi mita — ek click mein company ka sab kuch gaya |
| `related_name="+"` | Ulta raasta (`tenant.invoice_set`) band — 50 tables ke naam nahi takrayenge; query hamesha bachche ki taraf se: `Invoice.objects.filter(tenant=...)` |
| ⚠️ `public_id` ka default **Python** mein hai, database mein nahi | Raw SQL `INSERT` se row banao to `public_id` khud dena parega |

### `models/__init__.py` ka gotcha
Django models `core.models` se dhoondta hai. Model `__init__.py` mein import na hua → `makemigrations` kahega "No changes detected".

### Migration ka safar (khud dekha)
```bash
uv run src/manage.py makemigrations core   # models → Python file 0001_initial.py (DB ko nahi chhuta)
uv run src/manage.py sqlmigrate core 0001  # asal SQL dikhao, chalao nahi — har migration se pehle dekhne ki aadat
uv run src/manage.py migrate               # SQL chalao → core_tenant table
```
SQL mein dekha: `"id" bigint ... GENERATED BY DEFAULT AS IDENTITY`, `"public_id" uuid NOT NULL UNIQUE`, `timestamp with time zone`, aur `slug` ke liye extra `varchar_pattern_ops` index (`LIKE 'demo%'` jaisi search tez).
Migration files **hamesha commit** hoti hain — poori team ke paas same tables.

---

## Learning 6: `serializers.py` vs `schemas.py` — aur humne Django Ninja kyun chuna

**Date:** 25 Oct 2026 · **Lesson:** 5 se pehle (sawal: "company ke project mein `serializers.py` hai, hamare mein kyun nahi?")

### ORM aur serializer — do alag tarjuman
```
Postgres ⇄ ORM / Model ⇄ SERIALIZER (schema) ⇄ JSON ⇄ frontend / doosri services
```
| | Kaam | Kis se baat |
|---|---|---|
| Model / ORM (`models/`) | tables ↔ Python objects | Database |
| Serializer / Schema | Python objects ↔ JSON + aane wale data ki jaanch | Bahar ki duniya (API) |

### Serializer/schema ke 3 kaam
1. **Output** — model → JSON, **sirf chune hue fields** (`public_id` haan; `id`, `tenant_id`, password hash kabhi nahi).
2. **Input validation** — ghalat/khali data database tak pahunchne se pehle hi `400 Bad Request`.
3. **Shakal badalna** — date format, fields jorna waghera.

### Do libraries, ek hi kaam
| | Django REST Framework (DRF) | **Django Ninja (hamara faisla)** |
|---|---|---|
| File | `serializers.py` | **`schemas.py`** |
| Bunyaad | DRF ki apni serializer classes | **Pydantic** |
| Async | Kamzor (`adrf` package chahiye) | Built-in |
| Docs | Browsable API | `/api/docs` par Swagger (OpenAPI) khud |
| Company ka project | `serializers.py` dikha = DRF | — |

⚠️ **Ninja DRF ke upar nahi bana** — bilkul alag library hai (FastAPI se mutasir), DRF install hi nahi hota. Dono ka maqsad same (REST API), tareeqa alag. DRF ka concept seekhne ke liye: `serializers.py` ≈ `schemas.py`, `ViewSet`/`APIView` ≈ Ninja `Router` ke functions.

### Ninja kyun chuna
- **Pydantic har jagah ek** — API schemas, `env.py` (pydantic-settings), aur LangGraph ka structured output/state — ek hi cheez teen jagah.
- **Async built-in** — LangGraph async hai, SSE streaming async hai.
- Type hints se validation + Swagger docs khud.
- Reliable: Django ke upar patli layer, Pydantic v2 (Rust core) — production mein bohat istemal.

### Usool (dono mein)
Schema ka kaam **sirf shakal + jaanch**. Business rules (refund kab allowed) **sirf `services/`** mein — DRF mein log `serializer.create()` mein logic likh dete hain, hum nahi.

```python
# schemas.py (Ninja)
from ninja import ModelSchema, Schema

class TenantOut(ModelSchema):      # bahar jane wali shakal
    class Meta:
        model = Tenant
        fields = ["public_id", "name", "slug", "is_active", "created_at"]

class TenantIn(Schema):            # andar aane wali shakal
    name: str
    slug: str
```

---

## Learning 7: App ka naqsha — har file dekhte hi kya soch aaye

**Date:** 25 Oct 2026 · **Lesson:** 5 (`customers` app, pehli API)

### App kya hai?
**App = ek business area ka apna ghar** (customers, billing, tickets). Us ki table, rules, queries aur APIs sab usi ke andar. Har app ki shakal **bilkul ek jaisi** — ek samajh liya, sab samajh aa gaye.

```
src/
├── config/        project ka control room (app nahi): settings, env.py, urls.py, api.py ⭐
├── core/          APP — shared bunyaad: BaseModel, Tenant, tenancy.py, exceptions.py
└── apps/
    └── customers/ APP — customers ka ghar
```

### Har file → dimagh mein kya aaye
| File | Soch |
|---|---|
| `models/` | 🗄️ table kaisi hai |
| `services/` | ✍️ data **likhne/badalne** ke rules (`INSERT/UPDATE/DELETE`) |
| `selectors.py` | 📖 data **parhne** ki queries (`SELECT`) — library ka catalog, kuch badalta nahi |
| `schemas.py` | 📦 API mein data ki shakal + jaanch (DRF ka `serializers.py`) |
| `api.py` (app ka) | 🚪 is app ke darwaze/routes (MyCRMSim: `routes/contacts/routes.js`) |
| `config/api.py` | ⭐ saare darwazon ki **main list**, har app ek line (MyCRMSim: `routes/index.js`) |
| `core/tenancy.py` | 🛂 gate ka guard: "ye request kis company ki hai?" |
| `exceptions.py` | ❌ is app ki errors (code + HTTP status) |
| `utils.py` | 🔧 sirf is app ke chhote helpers |
| `__init__.py` | 🏪 package ka counter — folder ko package banata hai, cheezein bahar deta hai |
| `__all__` | 📋 counter par rakhi cheezon ki official list |

### `tenancy.py` — guard
Har request ka pehla sawal: **kis company ki?** `TenantHeader` header `X-Tenant-ID` padh kar `Tenant` dhoondta hai; mila → **`request.auth`** = wo Tenant; na mila → **401**.
Use: `Router(..., auth=TenantHeader())` — ek line, router ke **har** route par guard. Abhi header (arzi); JWT lesson mein login token — sirf `tenancy.py` badlegi.

### `selectors.py` vs `services/`
Selector sirf **parhta** hai, service **likhti** hai. Alag isliye: dhoondna aasan, ek query kai jagah (API, AI agent tool, report) — tenant filter kabhi nahi bhoolta. Django ki built-in cheez nahi — **HackSoft Django Styleguide** ka mashhoor tareeqa.

### `__init__.py` aur `__all__`
- `customers/__init__.py` khali — "ye package hai".
- `models/__init__.py` — model counter par (warna Django model nahi dekhta).
- `services/__init__.py` — `from apps.customers.services import create_customer` (andar file badle to bhi bahar ka import same).
- **Pydantic se koi talluq nahi** — ye Python ki apni cheezein hain.
- App ko **Django** start karta hai: `INSTALLED_APPS` mein `'apps.customers'` → `__init__.py` (darwaza) → `apps.py` (`name = 'apps.customers'`) → `models/`.

### Lesson 5 ke khaas sabaq
- ⭐ **Multi-tenant mein har unique rule mein `tenant`**: `UniqueConstraint(fields=["tenant", "phone"])`. Sirf `phone` unique hota to doosri company us number ka customer na bana pati — aur error se pata chal jata ke number kisi aur ke paas hai (leak).
- **Duplicate database ka constraint pakarta hai**, `exists()` check nahi — do requests ek pal mein aayein to dono `exists()` "nahi" kahenge (race condition). `IntegrityError` → `CustomerAlreadyExists` (409).
- **`get_customer` mein `tenant` filter** — UUID leak ho sakta hai; doosri company ko **404** (403 bhi nahi, warna pata chalta ke customer hai). UUID chhupata hai, tenant filter bachata hai.
- **`CustomerIn` mein `tenant` field nahi** — client tenant nahi chun sakta; sirf header/token se.
- `startapp` ka `name = 'customers'` → **`'apps.customers'`** (app `apps/` ke andar hai).
- Errors ka ek format: `DomainError` (`code` + `status_code`) + `config/api.py` ka `@api.exception_handler` → `{"code": "...", "message": "..."}`.
- Swagger docs khud: **http://127.0.0.1:8000/api/docs** (Authorize → `X-Tenant-ID`).

### Test natije (25 Oct 2026)
| # | Test | Natija |
|---|---|---|
| 1 | Ali Khan banao (`+92 300-123 4567`) | **201**, phone `+923001234567` (saaf), `id`/`tenant` jawab mein nahi |
| 2 | Wahi phone dobara (spaces ke bagair) | **409** `CUSTOMER_ALREADY_EXISTS` |
| 3 | Email `ali@` | **422** "There must be something after the @-sign" (Pydantic) |
| 4 | Bina header / kachra header | **401** |
| 5 | List (Demo Company) | **200** `{"items": [Ali], "count": 1}` |
| 6 | Ali by `public_id` (Demo Company) | **200** |
| 7a | List (NimbusTech) | **200** `{"items": [], "count": 0}` — Ali nazar nahi aaya ✅ |
| 7b | Ali by sahi `public_id` (NimbusTech) | **404** ✅ |
| 7c | Wahi phone NimbusTech mein | **201** — ek insaan, do companies, koi takrao nahi ✅ |

### ⚠️ Docker ka sabaq (aaj hua)
- Computer restart ke baad Docker Desktop band → Postgres nahi → `makemigrations` / Django shell **atak** gaye (error bhi nahi diya). Pehla shak hamesha: `docker compose ps`.
- Docker Desktop ko terminal tab se `& '...Docker Desktop.exe'` se chalaya, phir tab band kiya → **Docker bhi band** (tab ke saath us ka chalaya process bhi mar jata hai). Sahi: `Start-Process '...Docker Desktop.exe'` (alag process) ya Start Menu se.
- Docker Desktop → Settings → General → **"Start Docker Desktop when you sign in"** on kar do, phir restart ke baad khud chalega.
- `docker compose up -d --wait` — containers ke **healthy** hone tak ruk kar hi wapas aata hai.
