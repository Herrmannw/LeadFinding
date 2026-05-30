# LeadBot Frontend

Internal Next.js app for creating search jobs and viewing ranked leads.

## Environment

Create `leadbot/frontend/.env.local`:

```bash
DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres
```

`DATABASE_URL` is server-only. Do not expose it with `NEXT_PUBLIC_`.

## Run

```bash
npm install
npm run dev
```
