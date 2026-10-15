import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from src.provenance import recent_commune_services


class ServicesCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'cache.json'
        self.now=datetime(2026,10,14,18,tzinfo=timezone.utc)
        self.poi={"status":"available","scope":"commune","insee_code":"69123",
                  "method":"osm-commune-nwr-count-v1","relation_id":123,"area_id":3600000123,
                  "collected_at":"2026-10-14T08:00:00Z",
                  "counts":dict.fromkeys(["sport","park","supermarket","pharmacy","school","restaurant","hospital"],0)}
        self.poi['counts']['school']=1

    def read(self, poi=None):
        self.path.write_text(json.dumps({"cities":{"69123":{"poi_commune":self.poi if poi is None else poi}}}),encoding='utf-8')
        return recent_commune_services([self.path],now=self.now)

    def test_valid_zero_is_kept_and_old_or_future_records_rejected(self):
        self.assertEqual(self.read()['69123']['counts']['park'],0)
        self.assertEqual(self.read({**self.poi,'collected_at':'2026-10-01T00:00:00Z'}),{})
        self.assertEqual(self.read({**self.poi,'collected_at':'2026-10-15T00:00:00Z'}),{})

    def test_wrong_scope_commune_and_boundary_are_rejected(self):
        for change in ({'scope':'radius'},{'insee_code':'75056'},{'area_id':3600000999},{'status':'unavailable'}):
            self.assertEqual(self.read({**self.poi,**change}),{})

    def test_incomplete_invalid_counts_are_rejected(self):
        for counts in ({'park':0},{**self.poi['counts'],'park':-1},{**self.poi['counts'],'park':True}):
            self.assertEqual(self.read({**self.poi,'counts':counts}),{})

    def test_entirely_empty_collection_is_not_used_as_backup(self):
        self.assertEqual(self.read({**self.poi,'counts':dict.fromkeys(self.poi['counts'],0)}),{})

    def test_newest_valid_collection_wins(self):
        self.read()
        newer=Path(self.tmp.name)/'newer.json'
        updated={**self.poi,'collected_at':'2026-10-14T16:00:00Z','counts':{**self.poi['counts'],'park':5}}
        newer.write_text(json.dumps({'cities':{'69123':{'poi_commune':updated}}}),encoding='utf-8')
        self.assertEqual(recent_commune_services([newer,self.path],now=self.now)['69123']['counts']['park'],5)
