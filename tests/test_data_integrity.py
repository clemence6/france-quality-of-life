"""Régressions sur les erreurs de mesure identifiées par l'audit."""
import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
import pandas as pd
from src.extract.dvf import get_commune_stats
from src.extract.georisques import parse_risks_data
from src.extract.atmo import get_primary_pollution_value, get_air_quality_openaq
from src.extract.ban_geocode import geocode


class DataIntegrityTests(unittest.TestCase):
    def test_dvf_excludes_multiline_mutations_before_filtering(self):
        rows = [{"id_mutation": str(i), "code_commune": "75056", "type_local": "Appartement",
                 "date_mutation": "2025-02-01", "nature_mutation": "Vente",
                 "valeur_fonciere": 300000, "surface_reelle_bati": 50} for i in range(10)]
        rows += [{**rows[0], "id_mutation": "complex", "valeur_fonciere": 900000},
                 {**rows[0], "id_mutation": "complex", "type_local": "Dépendance", "code_commune": "75101"},
                 {**rows[0], "id_mutation": "missing", "surface_reelle_bati": 0}]
        stats = get_commune_stats(pd.DataFrame(rows), "75056", "Paris")
        self.assertEqual(stats["nb_ventes_totales"], 10)
        self.assertEqual(stats["by_type"]["apartment"]["median_price_m2"], 6000)
        self.assertIsNone(stats["by_type"]["house"]["median_price_m2"])

    def test_price_hidden_for_small_samples_and_no_name_fallback(self):
        frame = pd.DataFrame([{"id_mutation": "one", "code_commune": "06088", "type_local": "Maison",
                               "date_mutation": "2025-05-01", "nature_mutation": "Vente",
                               "valeur_fonciere": 400000, "surface_reelle_bati": 100}])
        self.assertIsNone(get_commune_stats(frame, "06088", "Nice")["prix_m2_median_global"])
        self.assertIsNone(get_commune_stats(frame, "44109", "Nice"))

    def test_absent_risks_are_not_zero(self):
        self.assertIsNone(parse_risks_data({"data": []})["total_risks"])
        self.assertEqual(parse_risks_data({"data": [{"risques_detail": []}]})["total_risks"], 0)
        with self.assertRaises(ValueError):
            parse_risks_data({"data": [{}]})

    def test_no_switch_between_pollutants_or_units(self):
        self.assertIsNone(get_primary_pollution_value({"measurements": {"no2": {"value": 30, "unit": "µg/m³"}}}))
        self.assertIsNone(get_primary_pollution_value({"measurements": {"pm25": {"value": 3, "unit": "ppm"}}}))
        self.assertEqual(get_primary_pollution_value({"measurements": {"pm25": {"value": 0, "unit": "µg/m³"}}}), 0)
        self.assertIsNone(get_primary_pollution_value({"measurements": {"pm25": {"value": float("nan"), "unit": "µg/m³"}}}))

    def test_wrong_geocoded_commune_is_rejected(self):
        with patch("src.extract.ban_geocode.requests.get") as get:
            get.return_value.json.return_value = {"features": [{"geometry": {"coordinates": [4, 45]}, "properties": {"citycode": "69123"}}]}
            with self.assertRaises(ValueError):
                geocode("Paris", insee_code="75056")
            self.assertEqual(get.call_args.kwargs["params"]["citycode"], "75056")

    def test_old_air_observation_is_rejected(self):
        station = {"id": 1, "coordinates": {"latitude": 48.85, "longitude": 2.35},
                   "sensors": [{"id": 3, "parameter": {"name": "pm25", "units": "µg/m³"}}]}
        old_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        with patch("src.extract.atmo.OPENAQ_API_KEY", "test-key"), patch("src.extract.atmo.requests.get") as get:
            get.return_value.status_code = 200
            get.return_value.json.side_effect = [{"results": [station]}, {"results": [{"sensorsId": 3, "value": 12, "datetime": {"utc": old_date}}]}]
            result = get_air_quality_openaq("Paris", 48.85, 2.35)
            self.assertEqual(result["measurements"], {})
            self.assertEqual(get.call_args_list[0].kwargs["params"]["radius"], 25000)


if __name__ == "__main__":
    unittest.main()
