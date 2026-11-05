# OpsPilot frontend

React 19 + Vite 8 + TypeScript client for the OpsPilot API: customer chat with live streaming, confirmation of agent writes, tickets with live progress, and a staff panel for refund approvals.

## Run

```bash
cd frontend
cp .env.example .env      # optional: change the proxy target or default company
npm install
npm run dev               # http://localhost:5173  (Django runserver must be on :8000)
```

Checks: `npm run typecheck`, `npm run lint`, `npm run build`.

Demo logins: customer `/demo-company/login` with phone `+923001234567`, staff `/staff/login` with `staff.demo-company`; both use `DEMO_PASSWORD` from the backend `.env`.

## Structure: MVC inside each feature

```text
src/
├─ app/          router (lazy pages), layouts, route guards, QueryClient
├─ shared/       api (fetch client with token refresh, SSE over fetch, errors), ui kit, lib
└─ features/
   ├─ auth/      model (api, store, zod schemas) · controller (hooks) · view (pages)
   ├─ chat/      streaming chat, confirmation card, agent details panel
   ├─ tickets/   list, new ticket, live timeline (SSE + Last-Event-ID)
   └─ staff/     refund approvals, customers
```

Model = data (API calls, types, schemas, stores). Controller = hooks with the logic. View = components that only render.

## Brand tokens

All colours live in `src/styles/index.css`: brand scales (`brand` Cockpit Navy, `beacon` Beacon Amber, `ink` neutrals, semantic `success/warning/danger/info`) and role tokens (`bg`, `surface`, `fg`, `primary`, `accent`, `line`...). Light and dark only change the role tokens, so components use classes like `bg-surface text-fg bg-primary` and never raw hex.

## Decisions

| Choice | Why |
|---|---|
| Vite proxy for `/api` | Same origin in development, so Django needs no CORS setup |
| `fetch` + `eventsource-parser` | `EventSource` cannot POST or send the Bearer token |
| TanStack Query for server data, Zustand only for the session and chats | No Redux; the cache, retries and loading states come from the query library |
| React Compiler (Babel preset) | Automatic memoization instead of hand-written `useMemo`/`useCallback` |
| Lazy route chunks | The login page does not download chat, markdown or staff code |
| Access token in memory, refresh token in `localStorage` | Practice-project trade-off; production should use an httpOnly cookie (needs a backend change) |
| Exact versions, `ignore-scripts` in `.npmrc` | Reproducible installs; package install scripts never run |
