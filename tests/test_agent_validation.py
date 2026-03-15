"""
Tests for AIAgent._validate_response — 5 anti-hallucination layers.
All external dependencies (OpenAI, EnrichedKnowledgeBase) are mocked.
"""
import unittest
from unittest.mock import patch, MagicMock


def _make_agent():
    """Create AIAgent with all external dependencies mocked."""
    with patch("ai_agent.EnrichedKnowledgeBase"), patch("ai_agent.OpenAI"):
        from ai_agent import AIAgent
        agent = AIAgent("fake-api-key", "https://larbreacafe.com")

    # Configure KB mock with realistic data
    agent.kb = MagicMock()
    agent.kb.get_department_mapping.return_value = {
        "75": "Paris",
        "91": "Essonne",
        "94": "Val-de-Marne",
    }
    agent.kb.get_all_boutiques.return_value = [
        {"name": "L'Arbre à Café Rue du Nil"},
        {"name": "L'Arbre à Café Rue des Martyrs"},
        {"name": "L'Arbre à Café Le Bon Marché Rive Gauche"},
        {"name": "L'Arbre à Café Rue Oberkampf"},
        {"name": "L'Arbre à Café Carrefour de l'Odéon"},
    ]
    agent.kb.get_boutique_by_ville = MagicMock(return_value=None)
    agent.get_boutique_info = MagicMock(
        return_value="[BOUTIQUE TROUVEE]\nRue du Nil, 75002 Paris"
    )
    return agent


class TestValidationLayer1BoutiqueContradiction(unittest.TestCase):
    """Layer 1: Negative phrase in response despite positive boutique context."""

    def setUp(self):
        self.agent = _make_agent()

    def test_negative_phrase_despite_boutique_context_is_flagged(self):
        response = "Malheureusement, nous n'avons pas de boutique dans cette zone."
        context = "[BOUTIQUE TROUVEE]\nRue du Nil, 75002 Paris"
        user_query = "boutique Paris 2"

        corrected, is_valid = self.agent._validate_response(response, context, user_query)

        self.assertFalse(is_valid)
        # Correction should NOT repeat the hallucinated negative phrase
        self.assertNotIn("n'avons pas de boutique", corrected)

    def test_valid_positive_response_passes_layer1(self):
        response = "Notre boutique Rue du Nil est ouverte du lundi au samedi."
        context = "[BOUTIQUE TROUVEE]\nRue du Nil, 75002 Paris"
        user_query = "boutique Paris 2"

        _, is_valid = self.agent._validate_response(response, context, user_query)

        self.assertTrue(is_valid)

    def test_no_boutique_in_context_skips_layer1(self):
        # Context has no boutique mention → layer 1 should not trigger
        response = "Nous n'avons pas de boutique dans cette ville."
        context = "Informations sur nos cafés d'origine."
        user_query = "boutique Lyon"

        _, is_valid = self.agent._validate_response(response, context, user_query)
        # Layer 1 not triggered → could still be valid
        self.assertTrue(is_valid)


class TestValidationLayer2ScheduleInconsistency(unittest.TestCase):
    """Layer 2: Hours in response differ from hours in context."""

    def setUp(self):
        self.agent = _make_agent()

    def test_wrong_hours_in_response_are_corrected(self):
        # Context has 9:00-19:00, response invents 8:00-22:00
        response = "La boutique est ouverte de 8:00-22:00 tous les jours."
        context = "Horaires: lundi-vendredi 9:00-19:00, samedi 10:00-19:00"
        user_query = "horaires boutique Nil"

        corrected, is_valid = self.agent._validate_response(response, context, user_query)

        self.assertFalse(is_valid)
        # Corrected response should use context hours
        self.assertIn("9:00-19:00", corrected)

    def test_correct_hours_pass_layer2(self):
        response = "Nous sommes ouverts de 9:00-19:00 en semaine."
        context = "Horaires: 9:00-19:00 lundi au vendredi"
        user_query = "horaires boutique"

        _, is_valid = self.agent._validate_response(response, context, user_query)

        self.assertTrue(is_valid)

    def test_response_without_hours_skips_layer2(self):
        response = "Notre boutique propose des cafés de spécialité."
        context = "Informations cafés Éthiopie"
        user_query = "cafés Éthiopie"

        _, is_valid = self.agent._validate_response(response, context, user_query)

        self.assertTrue(is_valid)


class TestValidationLayer4BoutiqueCount(unittest.TestCase):
    """Layer 4 [CRITIQUE]: Response claims wrong number of boutiques."""

    def setUp(self):
        self.agent = _make_agent()

    def test_wrong_count_is_corrected(self):
        # Actual count = 5, response claims 3
        response = "Nous avons 3 boutiques à Paris."
        context = "Liste de nos boutiques..."
        user_query = "combien de boutiques avez-vous ?"

        corrected, is_valid = self.agent._validate_response(response, context, user_query)

        self.assertFalse(is_valid)
        self.assertIn("5", corrected)
        self.assertNotIn("3 boutiques", corrected)

    def test_correct_count_passes_layer4(self):
        response = "Nous avons 5 boutiques à Paris."
        context = "Liste de nos boutiques..."
        user_query = "combien de boutiques avez-vous ?"

        _, is_valid = self.agent._validate_response(response, context, user_query)

        self.assertTrue(is_valid)

    def test_non_count_query_skips_layer4(self):
        response = "Voici nos horaires d'ouverture."
        context = "Horaires boutiques"
        user_query = "quels sont vos horaires ?"

        _, is_valid = self.agent._validate_response(response, context, user_query)

        self.assertTrue(is_valid)


class TestValidationLayer5PriceHallucination(unittest.TestCase):
    """Layer 5: Response mentions prices not present in context."""

    def setUp(self):
        self.agent = _make_agent()

    def test_invented_price_when_context_empty_is_removed(self):
        # Context has no prices, response invents a price
        response = "Nos cafés sont à partir de 12€ pour 250g."
        context = "Nous proposons des cafés d'origine unique d'Éthiopie et de Colombie."
        user_query = "prix des cafés"

        corrected, is_valid = self.agent._validate_response(response, context, user_query)

        self.assertFalse(is_valid)
        # Corrected response should not contain the invented price
        self.assertNotIn("12€", corrected)

    def test_price_present_in_context_passes_layer5(self):
        response = "Nos cafés sont proposés à partir de 12€."
        context = "Café Éthiopie Yirgacheffe 250g — 12€ TTC. Livraison offerte dès 49€."
        user_query = "prix des cafés"

        _, is_valid = self.agent._validate_response(response, context, user_query)

        self.assertTrue(is_valid)

    def test_aberrant_price_multiplied_is_corrected(self):
        # Context max price = 20€, response mentions 200€ (10x)
        response = "Ce café vaut 200€ pour 250g."
        context = "Café Éthiopie 250g — 20€ TTC."
        user_query = "prix café"

        corrected, is_valid = self.agent._validate_response(response, context, user_query)

        self.assertFalse(is_valid)

    def test_no_prices_anywhere_passes_layer5(self):
        response = "Bienvenue chez L'Arbre à Café, torréfacteur depuis 2009."
        context = "L'Arbre à Café est un torréfacteur parisien de cafés de spécialité."
        user_query = "qui êtes-vous ?"

        _, is_valid = self.agent._validate_response(response, context, user_query)

        self.assertTrue(is_valid)


if __name__ == "__main__":
    unittest.main()
