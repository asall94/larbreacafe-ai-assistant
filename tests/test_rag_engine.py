"""
Tests for RAGEngine document preparation — _prepare_documents() logic.
OpenAI API and file I/O are mocked to run without network or disk access.
"""
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json


SAMPLE_KB_DATA = {
    "total_boutiques": 2,
    "boutiques": [
        {
            "name": "L'Arbre à Café Rue du Nil",
            "adresse": "10 Rue du Nil - 75002 Paris",
            "telephone": "01 84 17 24 17",
            "email": "N/A",
            "horaires": {"lundi": "9h-19h", "dimanche": "Fermé"},
            "services": ["torréfaction sur place", "formation barista"],
            "url": "https://larbreacafe.com/boutique-nil",
        }
    ],
    "pages_par_categorie": {
        "cafes": [
            {
                "url": "https://larbreacafe.com/cafes/ethiopie",
                "title": "Café Éthiopie Yirgacheffe",
                "content": "Notes de dégustation : jasmin, fleur de mûrier, citrus. Torréfaction claire.",
            },
            {
                "url": "https://larbreacafe.com/cafes/colombie",
                "title": "Café Colombie Huila",
                "content": "Profil aromatique : caramel, noisette, pomme verte.",
            },
            {
                # Page without content — should NOT be indexed
                "url": "https://larbreacafe.com/cafes/vide",
                "title": "Page vide",
                "content": "",
            },
        ],
        "formations": [
            {
                "url": "https://larbreacafe.com/formations/barista",
                "title": "Formation Barista",
                "content": "Apprenez les bases de l'extraction espresso et du latte art.",
            }
        ],
    },
}


def _make_rag_engine():
    """Create RAGEngine with file I/O and OpenAI mocked."""
    with (
        patch("rag_engine.client"),
        patch.object(
            __import__("rag_engine", fromlist=["RAGEngine"]).RAGEngine,
            "_load_knowledge",
            return_value=SAMPLE_KB_DATA,
        ),
        patch.object(
            __import__("rag_engine", fromlist=["RAGEngine"]).RAGEngine,
            "_build_or_load_index",
        ),
    ):
        from rag_engine import RAGEngine
        engine = RAGEngine("fake_knowledge.json")
    return engine


class TestPrepareDocumentsFromPages(unittest.TestCase):
    """_prepare_documents must correctly index scraped page content."""

    def setUp(self):
        self.engine = _make_rag_engine()

    def test_pages_with_content_are_indexed(self):
        # 3 pages in "cafes" (1 empty) + 1 in "formations" = 3 valid page docs
        page_docs = [d for d in self.engine.documents if d["type"] == "page"]
        self.assertEqual(len(page_docs), 3)

    def test_empty_page_is_excluded(self):
        page_urls = [d["url"] for d in self.engine.documents if d["type"] == "page"]
        self.assertNotIn("https://larbreacafe.com/cafes/vide", page_urls)

    def test_page_document_has_required_fields(self):
        page_docs = [d for d in self.engine.documents if d["type"] == "page"]
        for doc in page_docs:
            self.assertIn("id", doc)
            self.assertIn("type", doc)
            self.assertIn("title", doc)
            self.assertIn("url", doc)
            self.assertIn("text", doc)
            self.assertEqual(doc["type"], "page")

    def test_page_category_is_preserved(self):
        cafes_docs = [
            d for d in self.engine.documents
            if d.get("type") == "page" and d.get("category") == "cafes"
        ]
        self.assertEqual(len(cafes_docs), 2)

    def test_page_text_content_is_indexed(self):
        ethiopie_docs = [
            d for d in self.engine.documents
            if "Éthiopie" in d.get("title", "") or "jasmin" in d.get("text", "")
        ]
        self.assertEqual(len(ethiopie_docs), 1)


class TestPrepareDocumentsFromBoutiques(unittest.TestCase):
    """_prepare_documents must include boutique data as searchable documents."""

    def setUp(self):
        self.engine = _make_rag_engine()

    def test_boutique_document_is_created(self):
        boutique_docs = [d for d in self.engine.documents if d["type"] == "boutique"]
        self.assertEqual(len(boutique_docs), 1)

    def test_boutique_document_contains_name(self):
        boutique_docs = [d for d in self.engine.documents if d["type"] == "boutique"]
        self.assertTrue(any("Nil" in d.get("text", "") for d in boutique_docs))

    def test_boutique_document_contains_address(self):
        boutique_docs = [d for d in self.engine.documents if d["type"] == "boutique"]
        self.assertTrue(
            any("75002" in d.get("text", "") or "Rue du Nil" in d.get("text", "") for d in boutique_docs)
        )

    def test_boutique_document_contains_phone(self):
        boutique_docs = [d for d in self.engine.documents if d["type"] == "boutique"]
        self.assertTrue(
            any("01 84 17 24 17" in d.get("text", "") for d in boutique_docs)
        )

    def test_boutique_document_contains_hours(self):
        boutique_docs = [d for d in self.engine.documents if d["type"] == "boutique"]
        # Hours should be integrated into the boutique text chunk
        self.assertTrue(
            any("lundi" in d.get("text", "").lower() for d in boutique_docs)
        )


class TestPrepareDocumentsTotal(unittest.TestCase):
    """Total document count and structure validation."""

    def setUp(self):
        self.engine = _make_rag_engine()

    def test_total_documents_count(self):
        # 3 valid pages + 1 boutique = 4 documents
        self.assertEqual(len(self.engine.documents), 4)

    def test_all_documents_have_id(self):
        for doc in self.engine.documents:
            self.assertIn("id", doc)
            self.assertIsInstance(doc["id"], str)

    def test_all_documents_have_non_empty_text(self):
        for doc in self.engine.documents:
            text = doc.get("text", "")
            self.assertGreater(len(text.strip()), 0, f"Empty text in doc: {doc.get('id')}")


class TestLoadKnowledge(unittest.TestCase):
    """_load_knowledge must correctly parse JSON file."""

    def test_load_knowledge_reads_json_file(self):
        sample_json = json.dumps(SAMPLE_KB_DATA)
        with (
            patch("builtins.open", mock_open(read_data=sample_json)),
            patch("rag_engine.client"),
            patch(
                "rag_engine.RAGEngine._build_or_load_index"
            ),
        ):
            from rag_engine import RAGEngine
            engine = RAGEngine.__new__(RAGEngine)
            engine.knowledge_file = "fake.json"
            engine.cache_file = "cache.pkl"
            engine.embedding_dim = 1536
            data = engine._load_knowledge()

        self.assertEqual(data["total_boutiques"], 2)
        self.assertIn("boutiques", data)
        self.assertIn("pages_par_categorie", data)


if __name__ == "__main__":
    unittest.main()
