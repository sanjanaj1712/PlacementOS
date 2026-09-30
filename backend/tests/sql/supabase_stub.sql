-- Minimal stand-in for the parts of Supabase that schema.sql depends on,
-- so the schema can be loaded into a plain local PostgreSQL for tests.

create schema if not exists auth;

create table if not exists auth.users (
    id uuid primary key,
    email text
);

create or replace function auth.uid()
returns uuid
language sql
stable
as $$
    select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'anon') then
        create role anon nologin;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'authenticated') then
        create role authenticated nologin;
    end if;
end;
$$;
