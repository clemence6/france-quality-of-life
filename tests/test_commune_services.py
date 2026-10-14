import unittest
from unittest.mock import Mock, patch
import requests
from src.extract.overpass_osm import commune_query, parse_commune_counts, POI_TAGS, get_commune_poi_counts, OVERPASS_ENDPOINTS


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

    def test_known_boundary_is_checked_again_and_cannot_be_injected(self):
        self.assertIn("relation(123)",commune_query("69123",relation_id=123))
        for unsafe in (True,0,-1,"123);node;"):
            with self.assertRaises(ValueError):
                commune_query("69123",relation_id=unsafe)
        data=self.response()
        data["elements"][0]["tags"]["ref:INSEE"]="75056"
        with self.assertRaises(ValueError):
            parse_commune_counts(data,"69123")

    def test_rate_limit_is_respected_before_backup_server(self):
        limited=Mock(status_code=429)
        limited.raise_for_status.side_effect=requests.HTTPError(response=limited)
        valid=Mock()
        valid.json.return_value=self.response()
        with patch("src.extract.overpass_osm.requests.post",side_effect=[limited,valid]) as post, patch("src.extract.overpass_osm.time.sleep") as sleep:
            result=get_commune_poi_counts("69123",relation_id=123)
            sleep.assert_called_once_with(30)
            self.assertEqual(result["api_endpoint"],OVERPASS_ENDPOINTS[1])
            self.assertEqual(post.call_count,2)


if __name__ == "__main__":
    unittest.main()
