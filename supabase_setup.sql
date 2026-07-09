create table if not exists public.client_brief_submissions (
  id uuid primary key,
  access_token text not null,
  status text not null default 'DRAFT',
  brief jsonb not null default '{}'::jsonb,
  client_email text,
  invite_message text,
  project_dir text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  submitted_at timestamptz,
  imported_at timestamptz
);

alter table public.client_brief_submissions enable row level security;

grant select, insert, update on table public.client_brief_submissions to service_role;

drop function if exists public.get_public_brief_submission(uuid, text);
create or replace function public.get_public_brief_submission(p_id uuid, p_access_token text)
returns setof public.client_brief_submissions
language sql
security definer
set search_path = public
as $$
  select *
  from public.client_brief_submissions
  where id = p_id
    and access_token = p_access_token
  limit 1;
$$;

drop function if exists public.save_public_brief_submission(uuid, text, jsonb);
create or replace function public.save_public_brief_submission(p_id uuid, p_access_token text, p_brief jsonb)
returns setof public.client_brief_submissions
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  update public.client_brief_submissions
     set brief = coalesce(p_brief, '{}'::jsonb),
         updated_at = now()
   where id = p_id
     and access_token = p_access_token
     and status in ('DRAFT', 'NEEDS_CHANGES')
  returning *;
end;
$$;

drop function if exists public.submit_public_brief_submission(uuid, text, jsonb);
create or replace function public.submit_public_brief_submission(p_id uuid, p_access_token text, p_brief jsonb)
returns setof public.client_brief_submissions
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  update public.client_brief_submissions
     set brief = coalesce(p_brief, '{}'::jsonb),
         status = 'SUBMITTED',
         submitted_at = now(),
         updated_at = now()
   where id = p_id
     and access_token = p_access_token
     and status in ('DRAFT', 'NEEDS_CHANGES')
  returning *;
end;
$$;

grant execute on function public.get_public_brief_submission(uuid, text) to anon, authenticated;
grant execute on function public.save_public_brief_submission(uuid, text, jsonb) to anon, authenticated;
grant execute on function public.submit_public_brief_submission(uuid, text, jsonb) to anon, authenticated;
