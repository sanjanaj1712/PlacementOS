-- Brings a database created before these fixes in line with schema.sql.
-- Runs in one transaction: if any step fails nothing is changed.
-- It does not delete any rows. If it stops on duplicate progress rows or
-- orphaned rows, it tells you which query to run to find them.

begin;

-- ---------------------------------------------------------
-- Goals: status, progress and target companies
-- ---------------------------------------------------------

alter table public.goals
    add column if not exists target_companies text[] not null default '{}',
    add column if not exists status text not null default 'not_started',
    add column if not exists progress_percentage integer not null default 0;

alter table public.goals drop constraint if exists goals_status_check;
alter table public.goals add constraint goals_status_check
    check (status in ('not_started', 'in_progress', 'achieved', 'abandoned'));

alter table public.goals drop constraint if exists goals_progress_percentage_check;
alter table public.goals add constraint goals_progress_percentage_check
    check (progress_percentage between 0 and 100);

-- ---------------------------------------------------------
-- Learning paths: ordering and subtopics
-- ---------------------------------------------------------

alter table public.learning_paths
    add column if not exists position integer not null default 0;

do $$
declare
    topic_id_type text;
begin
    if not exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'path_topics'
          and column_name = 'parent_topic_id'
    ) then
        select format_type(a.atttypid, a.atttypmod) into topic_id_type
        from pg_attribute a
        where a.attrelid = 'public.path_topics'::regclass
          and a.attname = 'id';

        execute format(
            'alter table public.path_topics add column parent_topic_id %s',
            topic_id_type
        );
    end if;
end;
$$;

-- ---------------------------------------------------------
-- Applications: pipeline statuses
-- ---------------------------------------------------------

do $$
declare
    constraint_name text;
begin
    for constraint_name in
        select conname from pg_constraint
        where conrelid = 'public.applications'::regclass
          and contype = 'c'
          and pg_get_constraintdef(oid) ilike '%status%'
    loop
        execute format(
            'alter table public.applications drop constraint %I',
            constraint_name
        );
    end loop;
end;
$$;

update public.applications set status = 'interested' where status = 'saved';

alter table public.applications alter column status set default 'interested';
alter table public.applications add constraint applications_status_check
    check (status in ('interested', 'applied', 'oa', 'interview', 'offer', 'rejected'));

-- ---------------------------------------------------------
-- Topic progress: one row per user and topic
-- To find duplicates:
--   select user_id, path_topic_id, count(*) from public.user_topic_progress
--   group by 1, 2 having count(*) > 1;
-- ---------------------------------------------------------

do $$
begin
    if exists (
        select 1 from public.user_topic_progress
        group by user_id, path_topic_id
        having count(*) > 1
    ) then
        raise exception 'user_topic_progress has duplicate (user_id, path_topic_id) rows; remove the extra rows and run this migration again';
    end if;

    if not exists (
        select 1 from pg_constraint
        where conrelid = 'public.user_topic_progress'::regclass
          and conname = 'user_topic_progress_user_id_path_topic_id_key'
    ) then
        alter table public.user_topic_progress
            add constraint user_topic_progress_user_id_path_topic_id_key
            unique (user_id, path_topic_id);
    end if;
end;
$$;

-- ---------------------------------------------------------
-- Foreign keys with ON DELETE CASCADE, so deleting an account, a learning
-- path or a topic never leaves orphaned rows behind.
-- ---------------------------------------------------------

do $$
declare
    fk record;
    constraint_name text;
begin
    for fk in
        select * from (values
            ('users', 'id', 'auth.users'),
            ('goals', 'user_id', 'auth.users'),
            ('applications', 'user_id', 'auth.users'),
            ('user_topic_progress', 'user_id', 'auth.users'),
            ('user_topic_progress', 'path_topic_id', 'public.path_topics'),
            ('path_topics', 'learning_path_id', 'public.learning_paths'),
            ('path_topics', 'parent_topic_id', 'public.path_topics')
        ) as t (table_name, column_name, referenced_table)
    loop
        for constraint_name in
            select c.conname
            from pg_constraint c
            join pg_attribute a
                on a.attrelid = c.conrelid
                and a.attnum = any (c.conkey)
            where c.conrelid = format('public.%I', fk.table_name)::regclass
              and c.contype = 'f'
              and a.attname = fk.column_name
        loop
            execute format(
                'alter table public.%I drop constraint %I',
                fk.table_name,
                constraint_name
            );
        end loop;

        execute format(
            'alter table public.%I add constraint %I foreign key (%I) references %s (id) on delete cascade',
            fk.table_name,
            fk.table_name || '_' || fk.column_name || '_fkey',
            fk.column_name,
            fk.referenced_table
        );
    end loop;
end;
$$;

-- ---------------------------------------------------------
-- Profiles: create on signup and backfill existing users
-- ---------------------------------------------------------

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.users (id, email)
    values (new.id, new.email)
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

insert into public.users (id, email)
select id, email from auth.users
on conflict (id) do nothing;

-- ---------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------

create index if not exists goals_user_id_created_at_idx
    on public.goals (user_id, created_at desc);
create index if not exists applications_user_id_created_at_idx
    on public.applications (user_id, created_at desc);
create index if not exists path_topics_learning_path_id_position_idx
    on public.path_topics (learning_path_id, position);
create index if not exists path_topics_parent_topic_id_idx
    on public.path_topics (parent_topic_id);
create index if not exists user_topic_progress_path_topic_id_idx
    on public.user_topic_progress (path_topic_id);

-- ---------------------------------------------------------
-- Row level security (see schema.sql for why)
-- ---------------------------------------------------------

alter table public.users enable row level security;
alter table public.goals enable row level security;
alter table public.learning_paths enable row level security;
alter table public.path_topics enable row level security;
alter table public.user_topic_progress enable row level security;
alter table public.applications enable row level security;

drop policy if exists "Users manage own profile" on public.users;
create policy "Users manage own profile" on public.users
    for all to authenticated
    using ((select auth.uid()) = id)
    with check ((select auth.uid()) = id);

drop policy if exists "Users manage own goals" on public.goals;
create policy "Users manage own goals" on public.goals
    for all to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users manage own progress" on public.user_topic_progress;
create policy "Users manage own progress" on public.user_topic_progress
    for all to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users manage own applications" on public.applications;
create policy "Users manage own applications" on public.applications
    for all to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

drop policy if exists "Signed-in users read learning paths" on public.learning_paths;
create policy "Signed-in users read learning paths" on public.learning_paths
    for select to authenticated
    using (true);

drop policy if exists "Signed-in users read path topics" on public.path_topics;
create policy "Signed-in users read path topics" on public.path_topics
    for select to authenticated
    using (true);

commit;
