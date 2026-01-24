from typing import List, Dict, Optional
import json
import os
import re
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

# Import RAG Engine (OBLIGATOIRE)
from rag_engine import RAGEngine

class EnrichedKnowledgeBase:
    """Enriched knowledge base for ALL larbrecaf boutiques"""
    
    def __init__(self):
        self.complete_file = "larbrecaf_knowledge_industrial_2025.json"
        self.demo_file = "larbrecaf_knowledge_demo.json"
        self.fallback_dir = "./data"
        self.data = self._load_complete_knowledge()
        
        # Adapt new structure
        self.boutiques = self.data.get('boutiques', [])
        self.infos_generales = self.data.get('informations_generales', {})
        
        # For compatibility with old system
        self.documents = self._create_documents_from_pages()
        
        # Initialize RAG Engine (MANDATORY)
        print("Initialisation RAG Engine...")
        # force_rebuild from env variable (default: True in production)
        force_rebuild = os.getenv('REBUILD_EMBEDDINGS', 'true').lower() == 'true'
        self.rag_engine = RAGEngine(self.complete_file, force_rebuild=force_rebuild)
        print("RAG Engine active - Recherche semantique disponible")
        
        print(f"Base enrichie chargee: {len(self.boutiques)} boutiques")
    
    def _create_documents_from_pages(self) -> List[Dict]:
        """Create documents from all scraped pages"""
        documents = []
        pages_categorie = self.data.get('pages_par_categorie', {})
        
        # Convert all pages to documents
        for category, pages in pages_categorie.items():
            for page in pages:
                if page.get('content'):
                    documents.append({
                        'url': page.get('url', ''),
                        'title': page.get('title', ''),
                        'text': page.get('content', ''),
                        'category': category
                    })
        
        return documents
    
    def _load_complete_knowledge(self) -> Dict:
        """Load complete knowledge base"""
        if os.path.exists(self.complete_file):
            try:
                with open(self.complete_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Check if has boutiques
                    if data.get('total_boutiques', 0) > 0:
                        return data
                    else:
                        print(f"[WARN] {self.complete_file} has 0 boutiques, trying demo file...")
            except Exception as e:
                print(f"Erreur chargement base complete: {e}")
        
        # Try demo file
        if os.path.exists(self.demo_file):
            print(f"[OK] Loading demo knowledge base: {self.demo_file}")
            try:
                with open(self.demo_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Erreur chargement base demo: {e}")
        
        # Old system fallback
        return self._load_old_format()
    
    def _load_old_format(self) -> Dict:
        """Load old format for compatibility"""
        data = {'boutiques': [], 'infos_generales': {}}
        
        docs_file = os.path.join(self.fallback_dir, "documents.json")
        
        if os.path.exists(docs_file):
            with open(docs_file, 'r', encoding='utf-8') as f:
                self.documents = json.load(f)
        
        return data
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Semantic search with RAG (mandatory)"""
        results = self.rag_engine.search(query, top_k=limit)
        
        # Format for compatibility with old format
        formatted_results = []
        for result in results:
            formatted_results.append({
                'type': result['type'],
                'content': result['content'],
                'score': result['score'],
                'metadata': result.get('metadata', {}),
                'data': result.get('data', {})
            })
        
        return formatted_results
    
    def get_all_boutiques(self) -> List[Dict]:
        """Return all boutiques"""
        return self.boutiques
    
    # Alias for backward compatibility
    def get_all_restaurants(self) -> List[Dict]:
        """Alias for backward compatibility (old name)"""
        return self.boutiques
    
    def _extract_ville_from_name(self, name: str) -> str:
        """Extract city from boutique name 'L''Arbre à Café City'"""
        # Remove 'L''Arbre à Café' prefix
        ville = name.replace('L''Arbre à Café', '').strip()
        return ville
    
    def get_boutique_by_ville(self, ville: str) -> Optional[Dict]:
        """Find boutique by city, department or postal code - 100% dynamic from KB"""
        ville_search = ville.lower().strip()
        
        # Search boutique (fuzzy matching with normalization)
        ville_lower = ville_search.lower()
        # Normalize for matching (remove hyphens and extra spaces)
        ville_normalized = ville_lower.replace('-', ' ').replace('  ', ' ').strip()
        # Also create version without spaces for partial word matching
        ville_compact = ville_normalized.replace(' ', '')
        
        for boutique in self.boutiques:
            # Extract city from name and address
            resto_ville = self._extract_ville_from_name(boutique.get('name', '')).lower()
            boutique_adresse = boutique.get('adresse', '').lower()
            
            # Normalize boutique data
            resto_ville_normalized = resto_ville.replace('-', ' ').replace('  ', ' ').strip()
            resto_adresse_normalized = boutique_adresse.replace('-', ' ')
            resto_ville_compact = resto_ville_normalized.replace(' ', '')
            
            # Multi-strategy matching (100% RAG - search in name AND address):
            # 1. Exact match in name
            if ville_lower in resto_ville or resto_ville.startswith(ville_lower):
                return boutique
            # 2. Normalized match in name
            if ville_normalized in resto_ville_normalized or resto_ville_normalized.startswith(ville_normalized):
                return boutique
            # 3. Compact match in name
            if resto_ville_compact in ville_compact or ville_compact.startswith(resto_ville_compact):
                return boutique
            # 4. Search in address (street names, postal codes, arrondissements)
            if ville_lower in resto_adresse or ville_normalized in resto_adresse_normalized:
                return boutique
            # 5. Match arrondissement (Paris 09, 9ème, 75009)
            code_postal = boutique.get('code_postal', '')
            if code_postal:
                # Extract arrondissement from postal code (75009 → 09)
                arr_match = re.search(r'75(\d{3})', code_postal)
                if arr_match:
                    arr_num = arr_match.group(1)
                    # Match: "paris 09", "09", "9", "9ème", "75009"
                    if any(pattern in ville_lower for pattern in [f'paris {arr_num}', f'paris{arr_num}', arr_num, arr_num.lstrip('0'), f'{arr_num.lstrip("0")}ème', code_postal.lower()]):
                        return boutique
            # 6. Partial word match in address (e.g., "nil" → "rue du nil")
            adresse_words = resto_adresse_normalized.split()
            search_words = ville_normalized.split()
            if any(search_word in adresse_words for search_word in search_words if len(search_word) > 2):
                return boutique
        
        return None
    
    # Alias for backward compatibility
    def get_boutique_by_ville(self, ville: str) -> Optional[Dict]:
        """Alias for backward compatibility"""
        return self.get_boutique_by_ville(ville)
    
    def get_contact_info(self, ville: Optional[str] = None) -> Dict:
        """Return contact info (for boutique or general)"""
        if ville:
            boutique = self.get_boutique_by_ville(ville)
            if boutique:
                return {
                    'boutique': boutique['name'],
                    'ville': self._extract_ville_from_name(boutique['name']),
                    'adresse': boutique['adresse'],
                    'telephone': boutique['telephone'],
                    'email': boutique.get('email', 'N/A'),
                    'services': boutique.get('services', []),
                    'url': boutique.get('url', '')
                }
        
        # General info
        return {
            'entreprise': 'larbrecaf',
            'nombre_boutiques': len(self.boutiques),
            'villes': [self._extract_ville_from_name(b['name']) for b in self.boutiques],
            'contact_general': self.infos_generales.get('contact_general', {}),
            'boutiques': self.boutiques
        }
    
    def get_hours(self, ville: Optional[str] = None) -> Dict:
        """Return hours (for boutique or all)"""
        if ville:
            boutique = self.get_boutique_by_ville(ville)
            if boutique:
                return {
                    'boutique': boutique['name'],
                    'ville': self._extract_ville_from_name(boutique['name']),
                    'horaires': boutique.get('horaires', {})
                }
        
        # All hours
        return {
            'boutiques': [
                {
                    'name': b['name'],
                    'ville': self._extract_ville_from_name(b['name']),
                    'horaires': b.get('horaires', {})
                } for b in self.boutiques
            ]
        }
    
    def get_info_generale(self, key: Optional[str] = None):
        """Return general info"""
        if key:
            return self.infos_generales.get(key)
        return self.infos_generales
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in km using Haversine formula"""
        R = 6371  # Earth radius in kilometers
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def find_nearest_boutique(self, ville_reference: str) -> Dict:
        """Find nearest boutique to a reference city using geocoding
        
        Args:
            ville_reference: City name to find nearest boutique from
            
        Returns:
            Dict with nearest boutique info and distance
        """
        # First try to geocode the reference city
        import requests
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': f"{ville_reference}, France",
                'format': 'json',
                'limit': 1
            }
            headers = {'User-Agent': 'larbrecafChatbot/1.0'}
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return {"error": f"Ville '{ville_reference}' non trouvée"}
            
            ref_lat = float(data[0]['lat'])
            ref_lon = float(data[0]['lon'])
            
        except Exception as e:
            return {"error": f"Erreur de géolocalisation: {str(e)}"}
        
        # Find nearest boutique with coordinates
        nearest = None
        min_distance = float('inf')
        
        for boutique in self.boutiques:
            coords = resto.get('coordinates')
            if not coords or not coords.get('lat') or not coords.get('lon'):
                continue
            
            distance = self.haversine_distance(
                ref_lat, ref_lon,
                coords['lat'], coords['lon']
            )
            
            if distance < min_distance:
                min_distance = distance
                nearest = boutique
        
        if not nearest:
            return {"error": "Aucune boutique avec coordonnées GPS disponibles"}
        
        return {
            'boutique': nearest['name'],
            'ville': self._extract_ville_from_name(nearest['name']),
            'adresse': nearest['adresse'],
            'distance_km': round(min_distance, 1),
            'telephone': nearest.get('telephone', ''),
            'url': nearest.get('url', '')
        }
    
    # Alias for backward compatibility
    def find_nearest_boutique(self, ville_reference: str) -> Dict:
        """Alias for backward compatibility"""
        return self.find_nearest_boutique(ville_reference)
    
    # Compatibility methods with old system
    def add_documents(self, documents: List[Dict]):
        """For compatibility - does nothing since enriched base is static"""
        pass
    

    
    def clear(self):
        """For compatibility - does nothing"""
        pass
    
    def get_department_mapping(self) -> Dict[str, str]:
        """100% RAG - Extract department mapping from boutiques data
        
        Returns:
            Dict mapping department codes and names to cities
        """
        mapping = {}
        
        # Extract from boutiques
        for boutique in self.boutiques:
            name = boutique.get('name', '')
            adresse = boutique.get('adresse', '')
            
            # Extract city from name "L''Arbre à Café {City}"
            ville = name.replace('L''Arbre à Café', '').strip()
            
            # Extract department code from address (postal code)
            import re
            postal_match = re.search(r'\b(\d{5})\b', adresse)
            if postal_match:
                postal = postal_match.group(1)
                dept_code = postal[:2]
                
                # Map department code to city
                mapping[dept_code] = ville
                
                # Add full department names
                dept_names = {
                    "91": "essonne",
                    "94": "val-de-marne",
                    "78": "yvelines",
                    "77": "seine-et-marne"
                }
                if dept_code in dept_names:
                    mapping[dept_names[dept_code]] = ville
        
        return mapping
    
    def get_all_cities(self) -> List[str]:
        """100% RAG - Extract all cities from boutiques data
        
        Returns:
            List of all city names
        """
        cities = []
        
        for boutique in self.boutiques:
            name = boutique.get('name', '')
            # Extract city from name "L''Arbre à Café {City}"
            ville = name.replace('L''Arbre à Café', '').strip()
            if ville and ville not in cities:
                cities.append(ville)
        
        return cities


# Alias for compatibility
KnowledgeBase = EnrichedKnowledgeBase
