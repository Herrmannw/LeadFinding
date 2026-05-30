# LeadBot Frontend

Internal Next.js app for creating search jobs and viewing ranked leads.

The frontend uses server-side database access only. Browser code does not connect to Supabase tables directly.

## Environment

Create `leadbot/frontend/.env.local`:

```bash
DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres
```

`DATABASE_URL` is server-only. Do not expose it with `NEXT_PUBLIC_`.

Do not add `NEXT_PUBLIC_SUPABASE_URL` or `NEXT_PUBLIC_SUPABASE_ANON_KEY` for table access unless the project explicitly adopts Supabase Auth/Data API access and adds matching RLS policies.

## Run

```bash
npm install
npm run dev
```
