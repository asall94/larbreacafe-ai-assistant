"""
Tests for AIAgent tool routing — execute_tool() dispatch and tool output formatting.
All external dependencies (OpenAI, EnrichedKnowledgeBase) are mocked.
"""
import unittest
from unittest.mock import patch, MagicMock


def _make_agent():
    """Create AIAgent with all external dependencies mocked."""
    with patch("ai_agent.EnrichedKnowledgeBase"), patch("ai_agent.OpenAI"):
        from ai_agent import AIAgent
        agent = AIAgent("fake-api-key", "https://larbreacafe.com")

    agent.kb = MagicMock()
    agent.kb.get_all_boutiques.return_value = [
        {
            "name": "L'Arbre à Café Rue du Nil",
            "adresse": "10 Rue du Nil - 75002 Paris",
            "telephone": "01 84 17 24 17",
            "url": "https://larbreacafe.com/boutique-nil",
        },
        {
            "name": "L'Arbre à Café Rue des Martyrs",
            "adresse": "35 rue des Martyrs - 75009 Paris",
            "telephone": "01 85 09 00 41",
            "url": "https://larbreacafe.com/boutique-martyrs",
        },
    ]
    agent.kb.search.return_value = []
    agent.kb.get_hours.return_value = {
        "boutiques": [
            {
                "name": "L'Arbre à Café Rue du Nil",
                "ville": "Rue du Nil",
                "horaires": {"lundi": "9h-19h", "dimanche": "Fermé"},
            }
        ]
    }
    agent.kb.get_contact_info.return_value = {
        "boutique": "L'Arbre à Café Rue du Nil",
        "ville": "Rue du Nil",
        "adresse": "10 Rue du Nil - 75002 Paris",
        "telephone": "01 84 17 24 17",
        "email": "N/A",
        "url": "https://larbreacafe.com/boutique-nil",
    }
    agent.kb.find_nearest_boutique.return_value = {
        "boutique": "L'Arbre à Café Rue du Nil",
        "ville": "Rue du Nil",
        "adresse": "10 Rue du Nil - 75002 Paris",
        "distance_km": 15.3,
        "telephone": "01 84 17 24 17",
        "url": "https://larbreacafe.com/boutique-nil",
    }
    agent.kb.get_department_mapping.return_value = {"75": "Paris"}
    agent.kb.get_all_cities = MagicMock(return_value=["Paris", "Rue du Nil"])
    return agent


class TestExecuteToolDispatch(unittest.TestCase):
    """execute_tool routes to the correct method for each tool name."""

    def setUp(self):
        self.agent = _make_agent()

    def test_unknown_tool_returns_error_message(self):
        result = self.agent.execute_tool("nonexistent_tool", {})
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_get_boutiques_tool_is_dispatched(self):
        result = self.agent.execute_tool("get_boutiques", {})
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_get_hours_no_params_returns_all_boutiques(self):
        result = self.agent.execute_tool("get_hours", {})
        self.assertIsInstance(result, str)

    def test_get_hours_with_ville_param(self):
        agent = _make_agent()
        agent.kb.get_hours.return_value = {
            "boutique": "L'Arbre à Café Rue du Nil",
            "ville": "Rue du Nil",
            "horaires": {"lundi": "9h-19h"},
        }
        result = agent.execute_tool("get_hours", {"ville": "Rue du Nil"})
        self.assertIsInstance(result, str)

    def test_get_contact_with_ville_param(self):
        result = self.agent.execute_tool("get_contact", {"ville": "Nil"})
        self.assertIsInstance(result, str)

    def test_find_nearest_boutique_tool(self):
        result = self.agent.execute_tool(
            "find_nearest_boutique", {"ville_reference": "Versailles"}
        )
        self.assertIsInstance(result, str)
        # Should mention distance
        self.assertIn("15.3", result)

    def test_search_knowledge_returns_hors_perimetre_when_no_results(self):
        self.agent.kb.search.return_value = []
        result = self.agent.execute_tool("search_knowledge", {"query": "question hors périmètre"})
        self.assertIn("HORS_PERIMETRE", result)


class TestGetBoutiquesFormatting(unittest.TestCase):
    """get_boutiques output must list all boutiques with addresses."""

    def setUp(self):
        self.agent = _make_agent()

    def test_output_contains_boutique_count(self):
        result = self.agent.get_boutiques()
        self.assertIn("2", result)

    def test_output_contains_all_phone_numbers(self):
        result = self.agent.get_boutiques()
        self.assertIn("01 84 17 24 17", result)
        self.assertIn("01 85 09 00 41", result)

    def test_output_contains_html_links(self):
        result = self.agent.get_boutiques()
        self.assertIn("<a href=", result)
        self.assertIn('target="_blank"', result)

    def test_output_contains_addresses(self):
        result = self.agent.get_boutiques()
        self.assertIn("Rue du Nil", result)
        self.assertIn("Martyrs", result)


class TestAgentTools6Defined(unittest.TestCase):
    """The agent must expose exactly 7 tools."""

    def setUp(self):
        self.agent = _make_agent()

    def test_exactly_6_tools_defined(self):
        self.assertEqual(len(self.agent.tools), 7)

    def test_all_expected_tool_names_present(self):
        tool_names = {t["name"] for t in self.agent.tools}
        expected = {
            "search_knowledge",
            "get_boutiques",
            "get_boutique_info",
            "get_contact",
            "get_hours",
            "find_nearest_boutique",
            "get_general_info",
        }
        self.assertEqual(tool_names, expected)

    def test_each_tool_has_name_and_description(self):
        for tool in self.agent.tools:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIsInstance(tool["name"], str)
            self.assertIsInstance(tool["description"], str)


class TestConversationMemory(unittest.TestCase):
    """Conversation memory is scoped per conversation_id."""

    def setUp(self):
        self.agent = _make_agent()

    def test_new_conversation_starts_empty(self):
        memory = self.agent._get_conversation_memory("conv-001")
        self.assertEqual(memory, [])

    def test_same_id_returns_same_list(self):
        mem1 = self.agent._get_conversation_memory("conv-42")
        mem1.append({"role": "user", "content": "Bonjour"})
        mem2 = self.agent._get_conversation_memory("conv-42")
        self.assertEqual(len(mem2), 1)

    def test_different_ids_are_isolated(self):
        mem_a = self.agent._get_conversation_memory("conv-A")
        mem_a.append({"role": "user", "content": "Question A"})
        mem_b = self.agent._get_conversation_memory("conv-B")
        self.assertEqual(len(mem_b), 0)


if __name__ == "__main__":
    unittest.main()
