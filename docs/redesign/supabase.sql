-- Tabelas opcionais do IDEAS CAPITAL assets (backend Supabase de pwass/store.py).
-- Rode no SQL Editor do Supabase. Uso pessoal, um único dono: as políticas abaixo só liberam o papel
-- "service_role" (a chave SUPABASE_KEY deve ser a service_role, guardada em secrets — nunca no repositório).
-- Nada sensível: sem saldo, número de conta, seed ou senha (o app recusa gravar esses campos).

do $$
declare t text;
begin
  foreach t in array array['watchlists','alertas','diario','analises_ia','filtros_salvos'] loop
    execute format('create table if not exists public.%I (
        id text primary key,
        doc jsonb not null,
        updated_at timestamptz not null default now())', t);
    execute format('alter table public.%I enable row level security', t);
    -- sem política para anon/authenticated => acesso negado; service_role ignora RLS por definição
    execute format('drop policy if exists "somente_service_role" on public.%I', t);
    execute format('create policy "somente_service_role" on public.%I for all to service_role using (true) with check (true)', t);
  end loop;
end $$;

-- Atualiza updated_at em cada gravação
create or replace function public.touch_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;
do $$
declare t text;
begin
  foreach t in array array['watchlists','alertas','diario','analises_ia','filtros_salvos'] loop
    execute format('drop trigger if exists touch on public.%I', t);
    execute format('create trigger touch before insert or update on public.%I for each row execute function public.touch_updated_at()', t);
  end loop;
end $$;
