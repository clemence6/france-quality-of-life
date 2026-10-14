"""Le cron doit signaler les échecs sans inventer des observations."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from src import main_pipeline as pipeline


class PipelineExecutionTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.tmp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.report_path = Path(self.tmp) / "run.json"
        self.city = {"name": "Bordeaux", "dept": "33", "insee": "33063"}
        self.geo = {"latitude": 44.8, "longitude": -0.5, "insee_code": "33063"}
        mocks = {
            "geocode": Mock(return_value=self.geo),
            "get_risks_by_commune": Mock(return_value={}),
            "parse_risks_data": Mock(return_value={"code_insee": "33063", "total_risks": 0, "risks": []}),
            "get_air_quality_openaq": Mock(return_value=None),
            "get_primary_pollution_value": Mock(return_value=None),
            "get_commune_poi_counts": Mock(return_value={"scope": "commune", "status": "available", "counts": {"park": 0}}),
            "download_dvf_department": Mock(return_value=object()),
            "get_commune_stats": Mock(return_value={"prix_m2_median_global": 4000, "nb_ventes_totales": 20}),
            "save_metadata": Mock(),
        }
        self.mocks = mocks
        self.stack.enter_context(patch.multiple(pipeline, **mocks))
        self.client = Mock()
        self.query = self.client.table.return_value.upsert.return_value
        self.query.execute.side_effect = lambda: Mock(data=[self.client.table.return_value.upsert.call_args.args[0]])

    def run_collection(self, cities=None):
        with contextlib.redirect_stdout(io.StringIO()):
            report = pipeline.run_pipeline(self.client, [self.city] if cities is None else cities,
                                          delay=0, report_path=self.report_path)
        self.assertEqual(report, json.loads(self.report_path.read_text(encoding="utf-8")))
        return report

    def test_success_and_expected_absent_air_are_reported(self):
        report = self.run_collection()
        self.assertTrue(report["success"])
        self.assertEqual(report["updated"], ["Bordeaux"])
        payload = self.client.table.return_value.upsert.call_args.args[0]
        self.assertIsNone(payload["air_quality_score"])
        self.assertEqual(payload["poi_park"], 0)
        self.mocks["save_metadata"].assert_called_once()

    def test_source_failure_is_not_a_success_or_a_zero(self):
        self.mocks["get_commune_poi_counts"].side_effect = RuntimeError("API indisponible")
        report = self.run_collection()
        self.assertFalse(report["success"])
        self.assertEqual(report["source_errors"][0]["source"], "Overpass")
        self.assertEqual(report["updated"], ["Bordeaux"])
        self.assertIsNone(self.client.table.return_value.upsert.call_args.args[0]["poi_park"])
        self.assertEqual(self.mocks["save_metadata"].call_args.args[2]["poi_commune"]["status"], "unavailable")

    def test_failed_city_does_not_stop_other_cities(self):
        self.mocks["geocode"].side_effect = [None, self.geo]
        report = self.run_collection([self.city, {**self.city, "name": "Ville suivante"}])
        self.assertFalse(report["success"])
        self.assertEqual(len(report["failed"]), 1)
        self.assertEqual(report["updated"], ["Ville suivante"])

    def test_uncovered_department_does_not_call_dvf(self):
        city = {"name": "Strasbourg", "dept": "67", "insee": "67482"}
        self.mocks["geocode"].return_value = {**self.geo, "insee_code": "67482"}
        self.mocks["parse_risks_data"].return_value = {"code_insee": "67482", "total_risks": 0}
        report = self.run_collection([city])
        self.assertTrue(report["success"])
        self.mocks["download_dvf_department"].assert_not_called()
        self.assertIsNone(self.client.table.return_value.upsert.call_args.args[0]["avg_price_m2"])

    def test_empty_database_response_does_not_certify_a_write(self):
        self.query.execute.side_effect = None
        self.query.execute.return_value = Mock(data=[])
        report = self.run_collection()
        self.assertFalse(report["success"])
        self.assertEqual(report["updated"], [])
        self.mocks["save_metadata"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
