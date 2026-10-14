import unittest
from src.extract.overpass_osm import commune_query, parse_commune_counts, POI_TAGS


class CommuneServicesTests(unittest.TestCase):
    def response(self):
        return {"elements": [
            {"type": "relation", "id": 123, "tags": {"ref:INSEE": "69123", "admin_level": "8", "name": "Lyon"}},
            {"type": "area", "id": 3600000123},
            *[{"type": "count", "tags": {"total": str(index)}} for index in range(len(POI_TAGS))],
        ]}

    def test_query_selects_commune_instead_of_radius_or_city_name(self):
        query = commune_query("69123")
        self.assertIn('["ref:INSEE"="69123"]', query)
        self.assertIn('["admin_level"="8"]', query)
        self.assertEqual(query.count("(area.commune)"), len(POI_TAGS))
        self.assertNotIn("around:", query)

    def test_verified_zero_and_output_order(self):
        result = parse_commune_counts(self.response(), "69123")
        self.assertEqual(result["scope"], "commune")
        self.assertEqual(result["counts"]["sport"], 0)
        self.assertEqual(result["counts"]["hospital"], 6)

    def test_missing_boundary_does_not_become_zero(self):
        data = self.response()
        data["elements"] = [e for e in data["elements"] if e["type"] == "count"]
        with self.assertRaises(ValueError):
            parse_commune_counts(data, "69123")

    def test_wrong_area_and_partial_response_rejected(self):
        data = self.response()
        data["elements"][1]["id"] = 3600000456
        with self.assertRaises(ValueError):
            parse_commune_counts(data, "69123")
        data = self.response()
        data["remark"] = "runtime error: timeout"
        with self.assertRaises(ValueError):
            parse_commune_counts(data, "69123")

    def test_incomplete_counts_and_injection_rejected(self):
        data = self.response()
        data["elements"].pop()
        with self.assertRaises(ValueError):
            parse_commune_counts(data, "69123")
        with self.assertRaises(ValueError):
            commune_query('69123"];node;')


if __name__ == "__main__":
    unittest.main()
