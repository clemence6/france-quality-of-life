// Renseigne ici les identifiants de TON projet Supabase.
// Le "anon key" est fait pour être exposé côté client — la sécurité réelle
// se fait via les policies RLS (Row Level Security) sur la table, pas en
// cachant cette clé. Assure-toi d'avoir une policy de lecture publique
// (SELECT) sur la table "cities_qol" avant de déployer ce site.
//
// Dashboard Supabase > Project Settings > API

const SUPABASE_CONFIG = {
  url: "https://nkvvwkuahsqkxzqrorkh.supabase.co",
  anonKey: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5rdnZ3a3VhaHNxa3h6cXJvcmtoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk1NzA1MjMsImV4cCI6MjEwNTE0NjUyM30.Z9MOhdFTWGQSya6U-AmfvowqkBJ7ceowbbH9fG619wo",
  table: "cities_qol",
};



