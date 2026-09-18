-- 🪦 조문객 수 정상화 (2026-09-19). 기존 프로젝트의 SQL Editor에 붙여넣고 Run.
-- 전엔 visitors() = 100 + 헌화 + 방명록 (가짜 패딩). 이제 = 실제로 다녀간 브라우저(anon id) 수.

create table if not exists visits (
  anon        text primary key,
  first_seen  timestamptz not null default now(),
  last_seen   timestamptz not null default now(),
  n           int not null default 1
);
alter table visits enable row level security;
drop policy if exists visits_read on visits; create policy visits_read on visits for select using (false);   -- 함수로만

-- 방문 기록 + 현재 조문객 수 반환. 같은 브라우저는 1명으로만 센다.
create or replace function visit(p_anon text)
returns int language plpgsql security definer set search_path = public as $$
begin
  if char_length(p_anon) between 6 and 64 then
    insert into public.visits(anon) values (p_anon)
    on conflict (anon) do update set last_seen = now(), n = visits.n + 1;
  end if;
  return (select count(*) from public.visits)::int;
end $$;

create or replace function visitors()
returns int language sql stable security definer set search_path = public as $$
  select (select count(*) from public.visits)::int;
$$;

grant execute on function visit(text) to anon, authenticated;
grant execute on function visitors() to anon, authenticated;
