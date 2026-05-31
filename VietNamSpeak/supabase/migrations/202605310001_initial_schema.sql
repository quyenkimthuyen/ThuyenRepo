create extension if not exists "pgcrypto";

create type review_state as enum ('new', 'learning', 'review', 'mastered');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  xp integer not null default 0,
  coins integer not null default 0,
  streak_count integer not null default 0,
  current_level integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.words (
  id uuid primary key default gen_random_uuid(),
  word text not null unique,
  ipa text not null,
  vn_pronunciation text not null,
  meaning_vi text not null,
  example_en text not null,
  example_vi text not null,
  audio_url text,
  topic text not null,
  level text not null check (level in ('beginner', 'elementary', 'intermediate', 'advanced')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.ipa_sounds (
  id uuid primary key default gen_random_uuid(),
  symbol text not null unique,
  vietnamese_hint text not null,
  examples jsonb not null default '[]'::jsonb,
  level text not null,
  created_at timestamptz not null default now()
);

create table public.pronunciation_rules (
  id uuid primary key default gen_random_uuid(),
  pattern text not null unique,
  ipa text not null,
  vietnamese_hint text not null,
  explanation text not null,
  examples text[] not null default '{}',
  created_at timestamptz not null default now()
);

create table public.user_word_progress (
  user_id uuid not null references auth.users(id) on delete cascade,
  word_id uuid not null references public.words(id) on delete cascade,
  state review_state not null default 'new',
  practice_count integer not null default 0,
  accuracy numeric(5,2) not null default 0,
  mastery_score numeric(5,2) not null default 0,
  repetitions integer not null default 0,
  interval_days integer not null default 0,
  ease_factor numeric(4,2) not null default 2.5,
  leitner_box integer not null default 1,
  next_review_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, word_id)
);

create table public.user_ipa_progress (
  user_id uuid not null references auth.users(id) on delete cascade,
  ipa_sound_id uuid not null references public.ipa_sounds(id) on delete cascade,
  practice_count integer not null default 0,
  accuracy numeric(5,2) not null default 0,
  mastery_score numeric(5,2) not null default 0,
  updated_at timestamptz not null default now(),
  primary key (user_id, ipa_sound_id)
);

create table public.favorites (
  user_id uuid not null references auth.users(id) on delete cascade,
  word_id uuid not null references public.words(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, word_id)
);

create table public.game_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  mode text not null,
  score integer not null default 0,
  xp_earned integer not null default 0,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create table public.game_answers (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.game_sessions(id) on delete cascade,
  word_id uuid references public.words(id) on delete set null,
  prompt_type text not null,
  answer text not null,
  correct_answer text not null,
  is_correct boolean not null,
  answered_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.words enable row level security;
alter table public.ipa_sounds enable row level security;
alter table public.pronunciation_rules enable row level security;
alter table public.user_word_progress enable row level security;
alter table public.user_ipa_progress enable row level security;
alter table public.favorites enable row level security;
alter table public.game_sessions enable row level security;
alter table public.game_answers enable row level security;

create policy "Public can read words" on public.words for select using (true);
create policy "Public can read ipa sounds" on public.ipa_sounds for select using (true);
create policy "Public can read pronunciation rules" on public.pronunciation_rules for select using (true);

create policy "Users can read own profile" on public.profiles for select using (auth.uid() = id);
create policy "Users can update own profile" on public.profiles for update using (auth.uid() = id);
create policy "Users can insert own profile" on public.profiles for insert with check (auth.uid() = id);

create policy "Users manage own word progress" on public.user_word_progress for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own ipa progress" on public.user_ipa_progress for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own favorites" on public.favorites for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own game sessions" on public.game_sessions for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users read answers for own sessions" on public.game_answers for select using (
  exists (select 1 from public.game_sessions s where s.id = session_id and s.user_id = auth.uid())
);
create policy "Users insert answers for own sessions" on public.game_answers for insert with check (
  exists (select 1 from public.game_sessions s where s.id = session_id and s.user_id = auth.uid())
);
