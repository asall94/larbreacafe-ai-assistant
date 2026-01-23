from typing import List, Dict, Optional, Tuple
from openai import OpenAI
import json
from datetime import datetime
from knowledge_base_enriched import EnrichedKnowledgeBase
from logger_config import setup_logger

# Setup structured JSON logging
logger = setup_logger(__name__)

class AIAgent:
    
    def __init__(self, openai_api_key: str, website_url: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.website_url = website_url
        self.kb = EnrichedKnowledgeBase()
        self.conversations = {}  # Dict[conversation_id, List[messages]]
        self.tools = self._define_tools()
        self.agent_state = {
            'knowledge_ready': True,
            'total_interactions': 0,
            'last_update': None,
            'total_queries': 0,
            'response_times': [],
            'tools_used_count': {},
            'last_tools_used': []
        }
        self.greeting_message = "Bonjour et bienvenue chez L''Arbre à Café.\nComment puis-je vous aider ?"
    
    def _get_conversation_memory(self, conversation_id: str) -> List[Dict]:
        """Get or create conversation memory for specific conversation_id"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        return self.conversations[conversation_id]
    
    def _define_tools(self) -> List[Dict]:
        return [
            {
                "name": "search_knowledge",
                "description": "Recherche informations sur cafés, torréfaction, origines, machines, formations, livraison, prix",
                "parameters": {"query": "Requête de recherche"}
            },
            {
                "name": "get_boutiques",
                "description": "OBLIGATOIRE pour: combien de boutiques, nombre de boutiques, liste des boutiques, toutes les boutiques, quelles boutiques. Retourne TOUTES les 4 boutiques à Paris avec adresses complètes",
                "parameters": {}
            },
            {
                "name": "get_boutique_info",
                "description": "Infos détaillées d'un boutique spécifique par ville, arrondissement, ou nom de rue (ex: 'Nil', 'Martyrs', 'Paris 07'). Recherche intelligente dans nom et adresse complète",
                "parameters": {"ville": "Nom ville/arrondissement/rue"}
            },
            {
                "name": "get_contact",
                "description": "Récupère les informations de contact (général ou d'un boutique spécifique)",
                "parameters": {"ville": "Nom de la ville (optionnel)"}
            },
            {
                "name": "get_hours",
                "description": "Récupère les horaires d'ouverture (tous ou d'un boutique spécifique)",
                "parameters": {"ville": "Nom de la ville (optionnel)"}
            },
            {
                "name": "find_nearest_boutique",
                "description": "Trouve le boutique L''Arbre à Café le plus proche d'une ville donnée",
                "parameters": {"ville_reference": "Nom de la ville de référence"}
            }
        ]
    
    def search_knowledge(self, query: str) -> str:
        """Enriched search across entire knowledge base - auto-detects department"""
        import re
        
        # Department detection in query - 100% RAG from KB
        query_lower = query.lower()
        dept_mapping = self.kb.get_department_mapping()  # Dynamic from KB
        
        # Check if department mentioned - replace dept name with ville
        dept_found = None
        
        # Paris arrondissements detection (4ème, 4e, 4eme → Paris 4e)
        arrondissement_match = re.search(r'(\d+)\s?(ème|e|eme)\s?arrondissement', query_lower)
        if arrondissement_match or 'paris 4' in query_lower or 'paris4' in query_lower:
            arr_num = arrondissement_match.group(1) if arrondissement_match else '4'
            query = re.sub(r'\d+\s?(ème|e|eme)\s?arrondissement', f'Paris {arr_num}e', query, flags=re.IGNORECASE)
            query = re.sub(r'paris\s?\d+', f'Paris {arr_num}e', query, flags=re.IGNORECASE)
            dept_found = f'Paris {arr_num}e'
            logger.info("Arrondissement detected", extra={"arr": arr_num, "query": query})
        else:
            # Standard department detection
            for dept, ville in dept_mapping.items():
                if dept in query_lower:
                    # Replace department name with city name
                    query = re.sub(rf'\b{dept}\b', ville, query, flags=re.IGNORECASE)
                    query = query.replace('essonne', ville).replace('val-de-marne', ville).replace('yvelines', ville).replace('seine-et-marne', ville)
                    dept_found = ville
                    logger.info("Department detected and replaced", extra={"dept": dept, "ville": ville, "query": query})
                    break
        
        # Enrich vague queries with conversation context (last boutique mentioned)
        # Get all cities dynamically from KB
        all_cities = self.kb.get_all_cities()  # Dynamic from KB
        vague_queries = ['url', 'lien', 'site', 'link', 'tel', 'telephone', 'adresse', 'address']
        if query_lower.strip() in vague_queries or (len(query.split()) <= 2 and not dept_found):
            # Skip context enrichment for now - would need conversation_id parameter
            pass
        
        results = self.kb.search(query, limit=5)
        
        if not results:
            return "[HORS_PERIMETRE] Cette information n'est pas disponible sur notre site web. Pour des questions spécifiques (parking, événements, réservations privées...), contactez directement le boutique concerné."
        
        context = []
        for result in results:
            # RAG already returns formatted content as string
            content = result.get('content', '')
            if content:
                context.append(content)
        
        return "\n\n".join(context)
    
    def get_boutiques(self) -> str:
        """Liste tous les boutiques L''Arbre à Café"""
        boutiques = self.kb.get_all_boutiques()
        
        if not boutiques:
            return "Aucun boutique disponible."
        
        # Extract unique regions from boutiques (100% dynamic)
        regions = set()
        for b in boutiques:
            addr = b.get('adresse', '')
            if 'Paris' in addr:
                regions.add('Paris')
        region_text = ', '.join(sorted(regions)) if regions else 'France'
        
        result = f"Nous avons {len(boutiques)} boutique{'s' if len(boutiques) > 1 else ''} à {region_text}:\n\n"
        
        for resto in boutiques:
            result += f"• {resto['name']}\n"
            result += f"   Adresse : {resto['adresse']}\n"
            result += f"   Téléphone : {resto['telephone']}\n"
            result += f"   Email : {resto['email']}\n"
            result += f"   Services : {', '.join(resto.get('services', []))}\n\n"
        
        return result
    
    def get_boutique_info(self, ville: str) -> str:
        """Detailed info for specific boutique - supports department and postal code"""
        # Use RAG for intelligent search
        results = self.kb.search(f"boutique {ville}", limit=3)
        
        if not results:
            # List all available boutiques
            all_restos = self.kb.get_all_boutiques()
            return f"Boutique non trouvée pour '{ville}'.\n\n" + \
                   f"NOS {len(all_restos)} BOUTIQUES DISPONIBLES:\n" + \
                   "\n".join([f"- {r.get('name', 'N/A')}" for r in all_restos[:10]]) + \
                   "\n\n(10 premiers boutiques affichés)"
        
        # Take best result
        best_result = results[0]
        return f"[BOUTIQUE TROUVEE]\n\n{best_result.get('content', 'Information non disponible')}"
    
    def get_contact(self, ville: Optional[str] = None) -> str:
        """Infos de contact"""
        contact = self.kb.get_contact_info(ville)
        
        if not contact:
            return f"Site web: {self.website_url}"
        
        if ville and contact.get('boutique'):
            result = f"Voici les coordonnées du boutique larbrecaf à {contact.get('ville', ville)} :\n\n"
            
            # Only show available fields (no N/A or "Non renseigné")
            if contact.get('adresse'):
                result += f"Adresse : {contact['adresse']}\n"
            
            if contact.get('telephone'):
                result += f"Téléphone : {contact['telephone']}\n"
            
            if contact.get('email') and contact['email'] != 'N/A':
                result += f"Email : {contact['email']}\n"
            
            # Add clickable link in HTML format
            if contact.get('url'):
                # Check if URL is generic boutiques page
                if '/nos-boutiques' in contact['url'] or '/content/70' in contact['url']:
                    result += f'\nRetrouvez toutes nos boutiques : <a href="{contact["url"]}" target="_blank">Nos boutiques</a>'
                else:
                    result += f'\nPlus d\'infos: <a href="{contact["url"]}" target="_blank">{contact["url"]}</a>'
        else:
            result = f"CONTACT larbrecaf\n\n"
            result += f"Entreprise: {contact.get('entreprise', 'L''Arbre à Café')}\n"
            result += f"Boutiques: {contact.get('nombre_boutiques', 0)} en Île-de-France\n"
            result += f"Villes: {', '.join(contact.get('villes', []))}\n\n"
            
            if contact.get('contact_general'):
                result += "Contact général:\n"
                for key, value in contact['contact_general'].items():
                    result += f"  {key}: {value}\n"
        
        return result
    
    def find_nearest_boutique(self, ville_reference: str) -> str:
        """Find nearest L''Arbre à Café boutique from a reference city"""
        result = self.kb.find_nearest_boutique(ville_reference)
        
        if result.get('error'):
            return f"[ERREUR] {result['error']}\n\nVoici la liste de tous nos boutiques:\n{self.get_boutiques()}"
        
        output = f"BOUTIQUE LA PLUS PROCHE DE {ville_reference.upper()}\n\n"
        output += f"Boutique: {result['boutique']}\n"
        output += f"Ville: {result['ville']}\n"
        output += f"Distance: {result['distance_km']} km\n"
        output += f"Adresse: {result['adresse']}\n"
        
        if result.get('telephone'):
            output += f"Téléphone: {result['telephone']}\n"
        if result.get('url'):
            # Check if URL is generic
            if '/nos-boutiques' in result['url'] or '/content/70' in result['url']:
                output += f'Retrouvez toutes nos boutiques : <a href="{result["url"]}" target="_blank">Nos boutiques</a>\n'
            else:
                output += f'Plus d\'infos: <a href="{result["url"]}" target="_blank">larbrecaf {result["ville"]}</a>\n'
        
        return output
    
    def get_hours(self, ville: Optional[str] = None) -> str:
        """Horaires d'ouverture"""
        hours = self.kb.get_hours(ville)
        
        if not hours:
            return "Horaires: Consultez notre site web"
        
        if ville and hours.get('boutique'):
            result = f"HORAIRES - {hours['boutique']} ({hours['ville']})\n\n"
            for jour, horaire in hours.get('horaires', {}).items():
                result += f"{jour.capitalize()} : {horaire}\n"
        else:
            result = "HORAIRES DE NOS BOUTIQUES :\n\n"
            for resto_hours in hours.get('boutiques', []):
                result += f"• {resto_hours['name']} ({resto_hours['ville']})\n"
                # Display ALL days, not just a sample
                for jour, horaire in resto_hours.get('horaires', {}).items():
                    result += f"  {jour.capitalize()} : {horaire}\n"
                result += "\n"
        
        return result
    
    def execute_tool(self, tool_name: str, parameters: Dict) -> str:
        """Execute tool with enriched tool set"""
        if tool_name == "search_knowledge":
            return self.search_knowledge(parameters.get("query", ""))
        elif tool_name == "get_boutiques":
            return self.get_boutiques()
        elif tool_name == "get_boutique_info":
            return self.get_boutique_info(parameters.get("ville", ""))
        elif tool_name == "get_contact":
            return self.get_contact(parameters.get("ville"))
        elif tool_name == "get_hours":
            return self.get_hours(parameters.get("ville"))
        elif tool_name == "find_nearest_boutique":
            return self.find_nearest_boutique(parameters.get("ville_reference", ""))
        else:
            logger.error("Unknown tool requested", extra={"tool_name": tool_name})
            return "Je n'ai pas pu traiter cette demande. Pourriez-vous reformuler votre question ?"
    
    def plan_and_execute(self, user_query: str, conversation_id: str = None) -> str:
        # Enrich vague queries with conversation context
        enriched_query = user_query
        if conversation_id and any(word in user_query.lower() for word in ['cela', 'ça', 'lien', 'url', 'source', 'où', 'it', 'that']):
            conversation_memory = self._get_conversation_memory(conversation_id)
            if len(conversation_memory) >= 2:
                # Get last user message
                for msg in reversed(conversation_memory[:-1]):
                    if msg.get('role') == 'user':
                        enriched_query = f"{msg.get('content', '')} {user_query}"
                        logger.info("Query enriched with conversation context", extra={"original": user_query, "enriched": enriched_query})
                        break
        
        # CRITICAL: Direct arrondissement detection BEFORE tool selection
        import re
        query_lower = enriched_query.lower()
        arrondissement_match = re.search(r'(\d+)\s?(ème|e|eme)\s?arrondissement', query_lower)
        if arrondissement_match or any(f'paris {i}' in query_lower for i in range(1, 21)):
            # Bypass planning - directly call search_knowledge with arrondissement detection
            logger.info("Arrondissement query detected - direct search_knowledge call")
            return self.search_knowledge(enriched_query)
        
        # 100% RAG - Build department rules dynamically from KB
        dept_mapping = self.kb.get_department_mapping()
        dept_rules = "\n".join([
            f'Si la question mentionne "{dept}" → utilise get_boutique_info avec ville="{dept}"'
            for dept in dept_mapping.keys()
            if dept.isdigit()  # Only numeric department codes
        ])
        
        # Add Paris arrondissements rule
        arrondissement_rule = "\nSi la question mentionne 'arrondissement' ou 'Paris 10e/10ème' → utilise search_knowledge avec la query complète (détection automatique)"
        
        # Generate boutique examples dynamically from KB (100% RAG)
        boutique_examples = []
        for b in self.kb.boutiques[:4]:  # Max 4 examples
            name = b.get('name', '').replace("L'Arbre à Café ", "")
            adresse = b.get('adresse', '')
            # Extract street name from address (e.g., "10 Rue du Nil - 75002 Paris" → "Nil")
            if adresse:
                street_parts = adresse.split('-')[0].strip()  # "10 Rue du Nil"
                street_words = street_parts.split()
                if len(street_words) >= 2:
                    # Last word of street (e.g., "Nil", "Martyrs", "Sèvres")
                    street_key = street_words[-1]
                    boutique_examples.append(f'   - "{street_key}", "{name}" → get_boutique_info avec ville="{street_key}" ou ville="{name}"')
        
        boutique_rules = "\n".join(boutique_examples) if boutique_examples else ""
        
        planning_prompt = f"""Tu es un agent IA autonome et intelligent pour le boutique L''Arbre à Café.

Outils disponibles:
{json.dumps(self.tools, indent=2, ensure_ascii=False)}

Question client: "{enriched_query}"

RÈGLES IMPORTANTES:

1. COMPTAGE/LISTE BOUTIQUES:
   - "combien", "nombre", "toutes", "liste", "quelles" → get_boutiques

2. BOUTIQUE SPÉCIFIQUE (exemples auto-générés depuis base):
{boutique_rules}

3. DÉPARTEMENTS (auto-généré depuis base):
{dept_rules}{arrondissement_rule}

Analyse la question et choisis les meilleurs outils.

Réponds UNIQUEMENT avec un JSON valide (pas de texte avant ou après):
{{
  "tools_to_use": [
    {{"tool": "nom_outil", "parameters": {{"param": "valeur"}}}}
  ]
}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Agent de planning multi-tool. Analyse query → Sélection outils optimaux → Output JSON strict (pas texte). Capacité: décomposition requêtes complexes en étapes parallèles."},
                    {"role": "user", "content": planning_prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            plan_text = response.choices[0].message.content.strip()
            
            plan_text = plan_text.replace('```json', '').replace('```', '').strip()
            
            try:
                plan = json.loads(plan_text)
            except:
                plan = {"tools_to_use": [{"tool": "search_knowledge", "parameters": {"query": user_query}}]}
            
            results = []
            for step in plan.get("tools_to_use", [])[:3]:
                tool_name = step.get("tool")
                parameters = step.get("parameters", {})
                result = self.execute_tool(tool_name, parameters)
                results.append(result)
                
                # Track tool usage
                if tool_name not in self.agent_state['tools_used_count']:
                    self.agent_state['tools_used_count'][tool_name] = 0
                self.agent_state['tools_used_count'][tool_name] += 1
                
                # Track tools used in this query
                if tool_name not in self.agent_state['last_tools_used']:
                    self.agent_state['last_tools_used'].append(tool_name)
            
            return "\n\n".join(results) if results else self.search_knowledge(user_query)
            
        except Exception as e:
            return self.search_knowledge(user_query)
    
    def _validate_response(self, response: str, context: str, user_query: str) -> Tuple[str, bool]:
        """Validate generated response against context and detect hallucinations
        
        Returns:
            (corrected_response, is_valid)
        """
        response_lower = response.lower()
        context_lower = context.lower()
        
        # 1. Check boutique contradictions
        if "[boutique trouvé]" in context_lower or "boutique" in context_lower:
            # Detect negative phrases when boutique exists
            negative_phrases = [
                "n'avons pas de boutique",
                "pas de boutique dans",
                "aucun boutique dans",
                "malheureusement pas",
                "ne disposons pas"
            ]
            
            for phrase in negative_phrases:
                if phrase in response_lower:
                    logger.warning("Boutique hallucination detected", extra={"phrase": phrase, "validation_result": "negative_phrase_despite_positive_context"})
                    # Return simple and direct corrected response
                    # Extract city/department from query - 100% RAG
                    import re
                    dept_mapping = self.kb.get_department_mapping()
                    dept_codes = [d for d in dept_mapping.keys() if d.isdigit()]
                    dept_pattern = r'\b(' + '|'.join(dept_codes) + r')\b'
                    dept_match = re.search(dept_pattern, user_query)
                    
                    if dept_match or any(d in user_query.lower() for d in dept_mapping.keys()):
                        # Use get_boutique_info for structured response
                        dept = dept_match.group(1) if dept_match else user_query
                        corrected = self.get_boutique_info(dept)
                        return corrected, False
                    # Otherwise return generic message based on context
                    return "Oui, nous avons plusieurs boutiques en Île-de-France. Pour plus de détails sur un boutique spécifique, précisez la ville ou le département.", False
        
        # 2. Check schedule inconsistencies
        import re
        # Extract hours from context (format HH:MM-HH:MM)
        context_hours = re.findall(r'\d{1,2}:\d{2}-\d{1,2}:\d{2}', context)
        # Extract hours from response (format HH:MM-HH:MM or HHhMM-HHhMM)
        response_hours = re.findall(r'\d{1,2}[h:]?\d{2}\s?-\s?\d{1,2}[h:]?\d{2}', response)
        
        if context_hours and response_hours:
            # Normalize for comparison
            def normalize_hour(h):
                # "11:30" or "11h30" → "1130"
                return re.sub(r'[:\sh-]', '', h)
            
            context_normalized = set(normalize_hour(h) for h in context_hours)
            response_normalized = set(normalize_hour(h) for h in response_hours)
            
            # If completely different hours
            if context_normalized and not any(rh in ' '.join(context_normalized) for rh in response_normalized):
                logger.warning("Schedule hallucination detected", extra={"context_hours": context_hours, "response_hours": response_hours})
                # Replace hours in response with context hours
                corrected = response
                for wrong_hour in response_hours:
                    # Replace with real context hours
                    if context_hours:
                        corrected = corrected.replace(wrong_hour, context_hours[0])
                return corrected, False
        
        # 3. Check department/city coherence - 100% RAG
        dept_mapping = self.kb.get_department_mapping()
        # Filter to numeric departments only and lowercase cities for comparison
        dept_ville = {
            dept: ville.lower() 
            for dept, ville in dept_mapping.items() 
            if dept.isdigit()
        }
        
        for dept, ville in dept_ville.items():
            # If question mentions department
            if dept in user_query.lower():
                # But response says "no boutique" AND context mentions the city
                if ville in context_lower and any(neg in response_lower for neg in ["pas de boutique", "aucun boutique"]):
                    logger.warning("Department contradiction detected", extra={"department": dept, "ville": ville})
                    # Use get_boutique_info for clean response
                    corrected = self.get_boutique_info(dept)
                    return corrected, False
        
        # 4. Check boutique count hallucinations - CRITICAL
        if any(word in user_query.lower() for word in ['combien', 'nombre', 'total']) and 'boutique' in user_query.lower():
            # Extract number from response
            count_match = re.search(r'(\d+)\s+boutiques?', response)
            if count_match:
                claimed_count = int(count_match.group(1))
                real_count = len(self.kb.get_all_boutiques())
                
                if claimed_count != real_count:
                    logger.warning("Boutique count hallucination detected", extra={
                        "claimed": claimed_count, 
                        "real": real_count,
                        "validation_result": "count_mismatch"
                    })
                    # Return exact corrected count
                    corrected = f"Nous avons {real_count} boutiques en France (Paris et Île-de-France principalement, ainsi que Lille et Versailles)."
                    return corrected, False
        
        # 5. Check aberrant or hallucinated prices
        context_prices = re.findall(r'(\d+[,.]?\d*)\s*€', context)
        response_prices = re.findall(r'(\d+[,.]?\d*)\s*€', response)
        
        # If response mentions prices BUT context has NONE → Hallucination
        if response_prices and not context_prices:
            logger.warning("Price hallucination detected", extra={"response_prices": response_prices, "context_empty": True})
            # Replace all prices with generic message
            corrected = re.sub(r'\d+[,.]?\d*\s*€', '', response)
            corrected += "\n\nPrix disponibles sur la carte en boutique. Contactez-nous pour plus d'informations."
            return corrected.strip(), False
        
        if context_prices and response_prices:
            context_nums = [float(p.replace(',', '.')) for p in context_prices]
            response_nums = [float(p.replace(',', '.')) for p in response_prices]
            
            # If price in response > 2x max of context
            if max(response_nums) > max(context_nums) * 2:
                logger.warning("Aberrant price detected", extra={"context_max": max(context_nums), "response_max": max(response_nums)})
                # Correct by replacing aberrant prices
                corrected = response
                for i, wrong_price in enumerate(response_prices):
                    if i < len(context_prices):
                        corrected = corrected.replace(f"{wrong_price}€", f"{context_prices[i]}€")
                return corrected, False
        
        # Valid response
        return response, True
    
    def chat(self, user_message: str, conversation_id: Optional[str] = None) -> str:
        import time
        start_time = time.time()
        
        self.agent_state['total_interactions'] += 1
        self.agent_state['total_queries'] += 1
        
        # Reset last_tools_used for this query
        self.agent_state['last_tools_used'] = []
        
        context = self.plan_and_execute(user_message, conversation_id)
        
        # Dynamically load boutique info
        boutiques = self.kb.get_all_boutiques()
        boutiques_info = []
        for resto in boutiques:
            # Extract city from boutique name "L''Arbre à Café {City}"
            name = resto.get('name', '')
            ville = name.replace('L''Arbre à Café', '').strip()
            telephone = resto.get('telephone', 'N/A')
            adresse = resto.get('adresse', 'N/A')
            boutiques_info.append(f"  * {ville} - {adresse} - Tel: {telephone}")
        boutiques_list = "\n".join(boutiques_info)
        
        system_prompt = f"""AGENTIC AI SYSTEM - Tool-First RAG Architecture

CRITICAL: You are a TOOL-CALLING agent. Tools have ALREADY been executed before this prompt. The context below contains the retrieved data. Your job is to SYNTHESIZE a natural response from this context.

IMPORTANT: NEVER mention tools in your response. Tools run invisibly in the background. User doesn't know about tools - just answer their question naturally based on the context provided.

LANGUAGE: Auto-detect query language (French/English). Respond in SAME language detected.

RETRIEVED CONTEXT FROM TOOLS (already executed):
{context}

GENERATION CONSTRAINTS:
- ALWAYS use at least 1 tool before responding. If unsure which tool, use search_knowledge with relevant keywords.
- Context is absolute source of truth. Never contradict retrieved data.
- If context empty AFTER tool execution: Say "Cette information n'est pas disponible sur le site pour le moment." + suggest contacting boutique directly.
- Schedules: Use exact format from context (8h-19h). If missing: "Ces horaires ne sont pas disponibles sur le site pour le moment."
- Prices: Only mention if present in context. If missing: "Les prix sont disponibles en boutique."
- Tasting notes/descriptions: Copy COMPLETE text from context. Do NOT simplify or omit details. Example: if context says "Jasmin, fleur de mûrier et de caféier, citrus, anette" → copy ALL 5 elements, never shorten to "jasmin, fleur de mûrier et citrus".
- Links: If context has HTML tags <a href>, copy EXACTLY as-is (preserve HTML).
- Source questions ("où", "lien", "url", "source"): If context lacks specific URL → provide general site + phone contact.
- Format: Plain text with line breaks for readability. NO markdown syntax (no bold/italic/underline markers).
- Long responses: Use double line breaks (\n\n) between distinct ideas/paragraphs for better readability.

MULTI-STEP REASONING EXAMPLES:
Query "cafés d'Éthiopie" → search_knowledge("Éthiopie origine café") → synthesize
Query "boutique à Paris" → get_boutiques() → filter Paris locations → respond with HTML links from context
Query "livraison offerte" → search_knowledge("livraison offerte montant") → extract info → respond

CONVERSATION CONTEXT:
You have access to last 10 messages. Use them to resolve references ("cela", "ça", "it", "that", "où as-tu vu").
When user asks about source/link for previous info, search for that topic in context.

RESPONSE STYLE: First-person plural, concise, conversational. Respect detected language.
"""

        # Get conversation-specific memory
        conversation_memory = self._get_conversation_memory(conversation_id)
        
        conversation_memory.append({
            "role": "user",
            "content": user_message
        })
        
        messages = [
            {"role": "system", "content": system_prompt}
        ] + conversation_memory[-10:]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1,  # Minimal for consistency while keeping some naturalness
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message.content
            
            # AUTOMATIC RESPONSE VALIDATION
            try:
                validated_message, is_valid = self._validate_response(assistant_message, context, user_message)
                
                if not is_valid:
                    logger.info("Response corrected by validator", extra={"validation_result": "invalid_corrected"})
                    assistant_message = validated_message
                else:
                    logger.info("Response validated successfully", extra={"validation_result": "valid"})
            except Exception as e:
                logger.error("Validation error", extra={"error_type": type(e).__name__}, exc_info=True)
                # In case of validation error, keep original response
            
            # POST-PROCESSING: Strip markdown syntax (bold, italic, underline) + convert markdown links to HTML
            import re
            # Convert markdown links [text](url) to HTML <a href="url">text</a>
            assistant_message = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', assistant_message)
            # Remove **bold**, __bold__
            assistant_message = re.sub(r'\*\*([^*]+)\*\*', r'\1', assistant_message)
            assistant_message = re.sub(r'__([^_]+)__', r'\1', assistant_message)
            # Remove *italic*, _italic_
            assistant_message = re.sub(r'(?<!\*)\*(?!\*)([^*]+)(?<!\*)\*(?!\*)', r'\1', assistant_message)
            assistant_message = re.sub(r'(?<!_)_(?!_)([^_]+)(?<!_)_(?!_)', r'\1', assistant_message)
            
            conversation_memory.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            # Track response time
            response_time = time.time() - start_time
            self.agent_state['response_times'].append(response_time)
            
            # Calculate average response time
            if self.agent_state['response_times']:
                avg_time = sum(self.agent_state['response_times']) / len(self.agent_state['response_times'])
                self.agent_state['avg_response_time'] = f"{avg_time:.2f}s"
            
            return assistant_message
            
        except Exception as e:
            logger.error("OpenAI API error", extra={"error_type": type(e).__name__, "error_message": str(e)}, exc_info=True)
            return f"Désolé, une erreur est survenue. Veuillez réessayer."
    
    def refresh_knowledge_from_web(self):
        """Rescrape website and update KB"""
        try:
            logger.info("Refreshing knowledge base...")
            
            # Scraper already has hardcoded data in extract_all_boutiques()
            
            # Could add real scraping here if necessary
            # For now, just reload enriched KB
            
            self.kb = EnrichedKnowledgeBase()
            self.agent_state['last_update'] = datetime.now().isoformat()
            
            boutique_count = len(self.kb.get_all_boutiques())
            logger.info("Knowledge base refreshed successfully", extra={"boutique_count": boutique_count})
            return True
            
        except Exception as e:
            logger.error("KB refresh failed", extra={"error_type": type(e).__name__}, exc_info=True)
            return False

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    agent = AIAgent(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        website_url="https://larbrecaf.com"
    )
    
    print(f"\nAgent ready with {len(agent.kb.get_all_boutiques())} boutiques!\n")
    
    test_queries = [
        "Où êtes-vous situés dans le 91 ?",
        "Quels sont vos plats végétariens ?",
        "Quel est le prix du Phở Bò ?",
        "Quels sont vos horaires d'ouverture ?"
    ]
    
    for query in test_queries:
        print(f"User: {query}")
        response = agent.chat(query)
        print(f"Agent: {response}\n")
