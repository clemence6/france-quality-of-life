"""La publication quotidienne garde le JSON disponible sans changer un bucket privé."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from src.provenance import publish_metadata, PUBLIC_METADATA_BUCKET


class MetadataPublicationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'provenance.json'
        self.path.write_text('{"cities": {}}', encoding='utf-8')
        self.client = Mock()

    def test_new_bucket_accepts_only_public_json_and_upserts(self):
        self.client.storage.list_buckets.return_value = []
        publish_metadata(self.client, self.path)
        options = self.client.storage.create_bucket.call_args.kwargs['options']
        self.assertTrue(options['public'])
        self.assertEqual(options['allowed_mime_types'], ['application/json'])
        self.client.storage.from_.assert_called_once_with(PUBLIC_METADATA_BUCKET)
        upload = self.client.storage.from_.return_value.upload.call_args
        self.assertEqual(upload.args[0], 'provenance.json')
        self.assertEqual(upload.args[1], self.path.read_bytes())
        self.assertEqual(upload.kwargs['file_options']['upsert'], 'true')

    def test_private_bucket_is_not_made_public(self):
        self.client.storage.list_buckets.return_value = [SimpleNamespace(id=PUBLIC_METADATA_BUCKET, public=False)]
        with self.assertRaises(RuntimeError):
            publish_metadata(self.client, self.path)
        self.client.storage.create_bucket.assert_not_called()
        self.client.storage.from_.assert_not_called()

    def test_invalid_document_is_not_published(self):
        self.path.write_text('{"cities": null}', encoding='utf-8')
        with self.assertRaises(ValueError):
            publish_metadata(self.client, self.path)
        self.client.storage.list_buckets.assert_not_called()
