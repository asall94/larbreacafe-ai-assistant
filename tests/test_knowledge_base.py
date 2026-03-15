"""
Tests for EnrichedKnowledgeBase — pure functions and KB lookups.
RAGEngine and file I/O are mocked to isolate business logic.
"""
import unittest
from unittest.mock import patch, MagicMock


SAMPLE_KB_DATA = {
    "total_boutiques": 2,
    "boutiques": [
        {
            "name": "L'Arbre à Café Rue du Nil",
            "adresse": "10 Rue du Nil - 75002 Paris",
            "telephone": "01 84 17 24 17",
            "email": "N/A",
            "code_postal": "75002",
            "horaires": {
                "lundi": "9h-19h",
                "mardi": "9h-19h",
                "mercredi": "9h-19h",
                "jeudi": "9h-19h",
                "vendredi": "9h-19h",
                "samedi": "10h-19h",
                "dimanche": "Fermé",
            },
            "url": "https://larbreacafe.com/boutique-nil",
            "statut": "ouvert",
            "coordinates": {"lat": 48.8637, "lon": 2.3494},
        },
        {
            "name": "L'Arbre à Café Rue des Martyrs",
            "adresse": "35 rue des Martyrs - 75009 Paris",
            "telephone": "01 85 09 00 41",
            "email": "N/A",
            "code_postal": "75009",
            "horaires": {
                "lundi": "8h-19h30",
                "mardi": "8h-19h30",
                "mercredi": "8h-19h30",
                "jeudi": "8h-19h30",
                "vendredi": "8h-19h30",
                "samedi": "8h-19h30",
                "dimanche": "8h-17h",
            },
            "url": "https://larbreacafe.com/boutique-martyrs",
            "statut": "ouvert",
            "coordinates": {"lat": 48.8822, "lon": 2.3385},
        },
    ],
    "informations_generales": {},
    "pages_par_categorie": {},
}


def _make_kb():
    """Create EnrichedKnowledgeBase with all external dependencies mocked."""
    with patch("knowledge_base_enriched.RAGEngine"), patch.object(
        __import__("knowledge_base_enriched", fromlist=["EnrichedKnowledgeBase"]).EnrichedKnowledgeBase,
        "_load_complete_knowledge",
        return_value=SAMPLE_KB_DATA,
    ):
        from knowledge_base_enriched import EnrichedKnowledgeBase
        return EnrichedKnowledgeBase()


class TestHaversineDistance(unittest.TestCase):
    """Tests for the Haversine formula (pure math function)."""

    def setUp(self):
        self.kb = _make_kb()

    def test_same_point_returns_zero(self):
        distance = self.kb.haversine_distance(48.8637, 2.3494, 48.8637, 2.3494)
        self.assertAlmostEqual(distance, 0.0, places=5)

    def test_paris_to_london_approx_340km(self):
        # Paris (48.8566, 2.3522) to London (51.5074, -0.1278)
        distance = self.kb.haversine_distance(48.8566, 2.3522, 51.5074, -0.1278)
        self.assertGreater(distance, 330)
        self.assertLess(distance, 360)

    def test_two_paris_boutiques_under_5km(self):
        # Rue du Nil (2e) to Rue des Martyrs (9e) — both central Paris
        distance = self.kb.haversine_distance(48.8637, 2.3494, 48.8822, 2.3385)
        self.assertLess(distance, 5)
        self.assertGreater(distance, 0)

    def test_returns_float(self):
        result = self.kb.haversine_distance(48.0, 2.0, 49.0, 3.0)
        self.assertIsInstance(result, float)


class TestGetAllBoutiques(unittest.TestCase):

    def setUp(self):
        self.kb = _make_kb()

    def test_returns_correct_count(self):
        boutiques = self.kb.get_all_boutiques()
        self.assertEqual(len(boutiques), 2)

    def test_returns_list_of_dicts(self):
        boutiques = self.kb.get_all_boutiques()
        self.assertIsInstance(boutiques, list)
        for b in boutiques:
            self.assertIsInstance(b, dict)

    def test_boutiques_have_required_fields(self):
        for b in self.kb.get_all_boutiques():
            self.assertIn("name", b)
            self.assertIn("adresse", b)
            self.assertIn("telephone", b)


class TestExtractVilleFromName(unittest.TestCase):

    def setUp(self):
        self.kb = _make_kb()

    def test_extracts_rue_du_nil(self):
        ville = self.kb._extract_ville_from_name("L'Arbre à Café Rue du Nil")
        self.assertEqual(ville, "Rue du Nil")

    def test_extracts_rue_des_martyrs(self):
        ville = self.kb._extract_ville_from_name("L'Arbre à Café Rue des Martyrs")
        self.assertEqual(ville, "Rue des Martyrs")

    def test_empty_name_returns_empty(self):
        ville = self.kb._extract_ville_from_name("")
        self.assertEqual(ville, "")


class TestGetBoutiqueByVille(unittest.TestCase):

    def setUp(self):
        self.kb = _make_kb()

    def test_exact_street_name_match(self):
        boutique = self.kb.get_boutique_by_ville("Nil")
        self.assertIsNotNone(boutique)
        self.assertIn("Nil", boutique["name"])

    def test_partial_name_match_martyrs(self):
        boutique = self.kb.get_boutique_by_ville("Martyrs")
        self.assertIsNotNone(boutique)
        self.assertIn("Martyrs", boutique["name"])

    def test_postal_code_match(self):
        boutique = self.kb.get_boutique_by_ville("75009")
        self.assertIsNotNone(boutique)
        self.assertIn("Martyrs", boutique["name"])

    def test_arrondissement_number_match(self):
        # Paris 2e → boutique Rue du Nil (75002)
        boutique = self.kb.get_boutique_by_ville("paris 02")
        self.assertIsNotNone(boutique)
        self.assertIn("Nil", boutique["name"])

    def test_unknown_ville_returns_none(self):
        boutique = self.kb.get_boutique_by_ville("Lyon")
        self.assertIsNone(boutique)

    def test_case_insensitive(self):
        boutique = self.kb.get_boutique_by_ville("NIL")
        self.assertIsNotNone(boutique)


class TestGetHours(unittest.TestCase):

    def setUp(self):
        self.kb = _make_kb()

    def test_get_hours_all_boutiques_returns_list(self):
        result = self.kb.get_hours()
        self.assertIn("boutiques", result)
        self.assertEqual(len(result["boutiques"]), 2)

    def test_get_hours_specific_boutique_returns_dict(self):
        result = self.kb.get_hours("Nil")
        self.assertIn("horaires", result)
        self.assertIn("boutique", result)
        self.assertIn("lundi", result["horaires"])

    def test_get_hours_unknown_boutique_returns_empty(self):
        result = self.kb.get_hours("Lyon")
        # No boutique found → returns all boutiques (default fallback)
        self.assertIn("boutiques", result)

    def test_hours_contain_schedule_values(self):
        result = self.kb.get_hours("Nil")
        horaires = result.get("horaires", {})
        self.assertEqual(horaires.get("lundi"), "9h-19h")
        self.assertEqual(horaires.get("dimanche"), "Fermé")


class TestGetContactInfo(unittest.TestCase):

    def setUp(self):
        self.kb = _make_kb()

    def test_contact_specific_boutique_returns_telephone(self):
        result = self.kb.get_contact_info("Nil")
        self.assertEqual(result.get("telephone"), "01 84 17 24 17")

    def test_contact_specific_boutique_returns_adresse(self):
        result = self.kb.get_contact_info("Martyrs")
        self.assertIn("Martyrs", result.get("adresse", ""))

    def test_contact_no_ville_returns_general_info(self):
        result = self.kb.get_contact_info()
        self.assertIn("nombre_boutiques", result)
        self.assertEqual(result["nombre_boutiques"], 2)

    def test_contact_general_has_villes_list(self):
        result = self.kb.get_contact_info()
        self.assertIn("villes", result)
        self.assertIsInstance(result["villes"], list)


class TestGetDepartmentMapping(unittest.TestCase):

    def setUp(self):
        self.kb = _make_kb()

    def test_returns_dict(self):
        mapping = self.kb.get_department_mapping()
        self.assertIsInstance(mapping, dict)

    def test_contains_paris_department_75(self):
        mapping = self.kb.get_department_mapping()
        # Both boutiques are in 75xxx → should have "75" mapped
        self.assertIn("75", mapping)

    def test_values_are_strings(self):
        mapping = self.kb.get_department_mapping()
        for key, value in mapping.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, str)


if __name__ == "__main__":
    unittest.main()
