-- 🪦 공동묘지 (Supabase). SQL Editor에 그대로 붙여넣고 Run.
-- 로그인 없음: 브라우저 익명 ID(anon)로만 중복 헌화를 막는다. anon key로 접근 → RLS로 허용 범위 제한.

create table if not exists tombs (
  id         bigint generated always as identity primary key,
  epitaph    text not null check (char_length(epitaph) <= 120),
  kind       text not null default 'chrys' check (kind in ('chrys','curse')),
  days       int,
  hanja      text,
  owner      text not null,                 -- 안치한 익명 ID
  flowers    int  not null default 0,
  created_at timestamptz not null default now(),
  seed       boolean not null default false
);

create table if not exists flowers (
  tomb_id    bigint not null references tombs(id) on delete cascade,
  anon       text not null,
  created_at timestamptz not null default now(),
  primary key (tomb_id, anon)
);

create table if not exists guestbook (
  id         bigint generated always as identity primary key,
  tomb_id    bigint not null references tombs(id) on delete cascade,
  anon       text not null,
  nick       text not null,
  text       text not null check (char_length(text) between 1 and 200),
  created_at timestamptz not null default now()
);

create index if not exists guestbook_tomb_idx on guestbook(tomb_id, id desc);

-- 헌화: (묘비, 익명) 1회만. 원자적으로 카운트 증가. 반환: 현재 개수 + 이미 했는지
create or replace function flower(p_tomb bigint, p_anon text)
returns table(flowers int, already boolean)
language plpgsql security definer set search_path = public as $$
declare inserted boolean;
begin
  insert into public.flowers(tomb_id, anon) values (p_tomb, p_anon)
  on conflict do nothing;
  inserted := found;
  if inserted then
    update public.tombs t set flowers = t.flowers + 1 where t.id = p_tomb;
  end if;
  return query select t.flowers, not inserted from public.tombs t where t.id = p_tomb;
end $$;

-- 조문객 = 실제로 다녀간 브라우저(anon id) 수. 페이지를 열 때 visit()로 기록한다. (migrate_visits.sql과 동일)
create table if not exists visits (
  anon        text primary key,
  first_seen  timestamptz not null default now(),
  last_seen   timestamptz not null default now(),
  n           int not null default 1
);

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

-- 내가 이미 헌화한 묘비 목록
create or replace function my_flowers(p_anon text)
returns setof bigint language sql stable security definer set search_path = public as $$
  select tomb_id from public.flowers where anon = p_anon;
$$;

-- RLS: 누구나 읽기, 묘비/방명록 쓰기는 허용, 수정·삭제 금지. flowers 테이블은 함수로만.
alter table tombs     enable row level security;
alter table flowers   enable row level security;
alter table guestbook enable row level security;
alter table visits    enable row level security;

drop policy if exists tombs_read on tombs;      create policy tombs_read     on tombs     for select using (true);
drop policy if exists tombs_insert on tombs;    create policy tombs_insert   on tombs     for insert with check (owner is not null and char_length(owner) between 6 and 64);
drop policy if exists gb_read on guestbook;     create policy gb_read        on guestbook for select using (true);
drop policy if exists gb_insert on guestbook;   create policy gb_insert      on guestbook for insert with check (char_length(anon) between 6 and 64);
drop policy if exists fl_read on flowers;       create policy fl_read        on flowers   for select using (false);   -- 직접 조회 불가 (함수로만)
drop policy if exists visits_read on visits;    create policy visits_read    on visits    for select using (false);

grant execute on function flower(bigint, text) to anon, authenticated;
grant execute on function visitors() to anon, authenticated;
grant execute on function visit(text) to anon, authenticated;
grant execute on function my_flowers(text) to anon, authenticated;

-- 시드 (비어 있을 때만)
insert into tombs (epitaph, kind, days, hanja, owner, flowers, seed)
select * from (values
  ('"3년 연애 후 ''우리 잠깐 시간을 갖자'' → 잠수"', 'curse', 1095, '來去無常', 'seed', 2914, true),
  ('"청첩장 돌리기 3주 전 파혼"', 'curse', 1460, '前緣已斷 後悔未斷', 'seed', 2105, true),
  ('"200일 선물 주고 그날 밤 환승 발각"', 'chrys', 200, null, 'seed', 1888, true),
  ('"바쁘다며 스토리는 1분마다 올리던 그대"', 'curse', 240, '戀愛即逃', 'seed', 142, true),
  ('"읽씹 6시간, 답장은 ''ㅇㅇ'' 두 글자"', 'chrys', 98, null, 'seed', 88, true),
  ('"나만 좋아했던 것 같은 6개월"', 'curse', 180, '前任常思', 'seed', 231, true),
  ('"먼저 좋다 해놓고 먼저 식은 사람"', 'chrys', 130, null, 'seed', 67, true)
) as v(epitaph, kind, days, hanja, owner, flowers, seed)
where not exists (select 1 from tombs);
