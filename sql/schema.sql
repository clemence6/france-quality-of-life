-- Table alimentée par src/main_pipeline.py et lue par web/app.js
-- La contrainte UNIQUE sur insee_code est nécessaire pour que
-- upsert(payload, on_conflict="insee_code") fonctionne correctement.

create table if not exists cities_qol (
  insee_code text primary key,
  city_name text not null,
  postal_code text,
  latitude double precision,
  longitude double precision,
  risks_count integer,
  poi_sport integer default 0,
  poi_park integer default 0,
  poi_supermarket integer default 0,
  poi_pharmacy integer default 0,
  poi_school integer default 0,
  poi_restaurant integer default 0,
  poi_hospital integer default 0,
  avg_price_m2 numeric,
  total_transactions integer,
  air_quality_score numeric,
  updated_at timestamptz default now()
);

-- Row Level Security : la table doit être lisible publiquement pour que
-- le dashboard (web/) puisse la lire avec la clé "anon".
-- Migration : si ta table cities_qol existe déjà (créée avant l'ajout du
-- code postal), ajoute simplement la colonne sans tout recréer :
--   alter table cities_qol add column if not exists postal_code text;

alter table cities_qol enable row level security;

create policy "Public read access"
  on cities_qol
  for select
  using (true);

-- (Aucune policy d'écriture publique : les insert/update se font uniquement
-- depuis main_pipeline.py avec la clé "service_role", pas la clé anon.)
