"""Le contrôle quotidien détecte des incohérences sans certifier les lignes fautives."""
import copy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import pandas as pd

from src.daily_audit import build_report
from src.extract.dvf import get_commune_stats
from src.provenance import snapshot, publish_metadata


class DailyAuditTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
        self.city = {"insee": "33063", "name": "Bordeaux", "dept": "33"}
        self.frame = pd.DataFrame([{"id_mutation": str(i), "date_mutation": "2025-06-01",
            "nature_mutation": "Vente", "valeur_fonciere": 200000, "code_commune": "33063",
            "type_local": "Appartement", "surface_reelle_bati": 50} for i in range(12)])
        self.row = {"insee_code": "33063", "updated_at": "2026-10-18T10:00:00+00:00",
                    "latitude": 44.8, "longitude": -.5, "avg_price_m2": 4000,
                    "total_transactions": 12, "risks_count": 0, "air_quality_score": None,
                    **{"poi_"+key: 0 for key in ("sport", "park", "supermarket", "pharmacy", "school", "restaurant", "hospital")}}
        self.metadata = {"snapshot": snapshot(self.row), "geocoding": {"insee_code": "33063", "latitude": 44.8, "longitude": -.5},
            "risks": {"code_insee": "33063", "risks": [], "total_risks": 0},
            "air": {"measurements": {}}, "poi_commune": {"status": "available", "scope": "commune",
                "insee_code": "33063", "relation_id": 123, "area_id": 3600000123,
                "method": "osm-commune-nwr-count-v1", "collected_at": "2026-10-18T10:00:00+00:00",
                "counts": {key.removeprefix("poi_"): value for key, value in self.row.items() if key.startswith("poi_")}},
            "dvf": {**get_commune_stats(self.frame, "33063", "Bordeaux"), "year": 2025}}

    def report(self, rows=None, frames=None):
        return build_report([self.row] if rows is None else rows,
            {"cities": {"33063": self.metadata}}, {"33": self.frame} if frames is None else frames,
            [self.city], self.now)

    def test_recalculation_and_documented_zero_pass(self):
        report = self.report()
        self.assertTrue(report["success"])
        self.assertEqual(report["summary"]["passed"], 1)
        self.assertEqual(report["cities"]["33063"]["snapshot"], snapshot(self.row))

    def test_database_drift_fails_without_certifying_metadata(self):
        self.row["poi_park"] = 100
        report = self.report()
        self.assertFalse(report["success"])
        self.assertNotIn("snapshot", report["cities"]["33063"])

    def test_same_snapshot_does_not_hide_bad_median(self):
        self.metadata["dvf"]["by_type"]["apartment"]["median_price_m2"] = 8000
        self.assertFalse(self.report()["success"])

    def test_missing_city_and_missing_cache_are_failures(self):
        self.assertEqual(self.report(rows=[])["summary"]["failed"], 1)
        self.assertFalse(self.report(frames={})["success"])

    def test_wrong_territory_and_stale_services_fail(self):
        original = copy.deepcopy(self.metadata)
        self.metadata["poi_commune"]["scope"] = "radius"
        self.assertFalse(self.report()["success"])
        self.metadata = original
        self.metadata["poi_commune"]["collected_at"] = "2026-10-01T10:00:00+00:00"
        self.assertFalse(self.report()["success"])

    def test_report_can_publish_to_separate_public_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily-audit.json"
            path.write_text('{"cities": {}}', encoding="utf-8")
            client = Mock()
            client.storage.list_buckets.return_value = []
            publish_metadata(client, path, object_name="audit.json")
            self.assertEqual(client.storage.from_.return_value.upload.call_args.args[0], "audit.json")
            with self.assertRaises(ValueError):
                publish_metadata(client, path, object_name="private.env")


if __name__ == "__main__":
    unittest.main()
