import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Set
import re
from urllib.parse import urljoin, urlparse

class larbrecafIndustrialScraper:
    """Complete industrial scraper - Automatically scrapes ALL relevant pages"""
    
    def __init__(self, base_url: str = "https://larbreacafe.com"):
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'larbrecafChatbot/1.0 (https://github.com/asall94/agentic-rag-larbrecaf)'
        }
        self.visited_urls: Set[str] = set()
        self.all_pages_content = {}
        self.boutiques = []
        self.produits = []
        self.geocoding_cache = {}  # Cache for Nominatim API calls
        self.max_depth = 1  # Maximum crawl depth (increased for complete coverage)
        self.max_pages = None  # No limit - scrape everything relevant
        
        # Pages to ignore (files, external resources)
        self.ignored_patterns = [
            '/wp-content/', '/wp-admin/', '/wp-includes/',
            '.jpg', '.png', '.gif', '.pdf', '.zip', '.doc', '.xml',
            '#', 'javascript:', 'mailto:', 'tel:',
            '/feed/', '/author/', '/tag/', '/category/',  # WordPress cruft
            '/page/', '/search/'  # Pagination/search pages
        ]
    
    def should_scrape_url(self, url: str) -> bool:
        """Determine if URL should be scraped"""
        # Ignore external URLs
        parsed_base = urlparse(self.base_url)
        parsed_url = urlparse(url)
        
        # Allow both main domain and subdomains (e.g., boutiques.larbrecaf.com)
        base_domain = parsed_base.netloc.replace('www.', '')
        url_domain = parsed_url.netloc.replace('www.', '')
        
        if base_domain not in url_domain:
            return False
        
        # Ignore patterns
        for pattern in self.ignored_patterns:
            if pattern in url.lower():
                return False
        
        # Already visited
        if url in self.visited_urls:
            return False
        
        # Limit total pages (if set)
        if self.max_pages and len(self.visited_urls) >= self.max_pages:
            return False
        
        return True
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove empty lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def scrape_page(self, url: str) -> Dict:
        """Scrape complete page and extract content"""
        try:
            print(f"Scraping: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unnecessary elements
            for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'noscript']):
                element.decompose()
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ""
            
            # Extract headings (structure)
            headings = []
            for tag in ['h1', 'h2', 'h3']:
                for heading in soup.find_all(tag):
                    text = heading.get_text(strip=True)
                    if text and len(text) > 2:
                        headings.append({
                            'level': tag,
                            'text': text
                        })
            
            # Extract main content
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            text_content = main_content.get_text(separator='\n', strip=True) if main_content else ""
            text_content = self.clean_text(text_content)
            
            # Extract lists (FAQ, key points)
            lists = []
            for ul in soup.find_all(['ul', 'ol']):
                items = [li.get_text(strip=True) for li in ul.find_all('li')]
                if items:
                    lists.append(items)
            
            self.visited_urls.add(url)
            
            return {
                'url': url,
                'title': title_text,
                'headings': headings,
                'content': text_content[:5000],  # Limit to 5000 chars
                'lists': lists,
                'scraped_at': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            print(f"  Erreur: {e}")
            return None
    
    def discover_pages(self, start_url: str, depth: int = 0) -> List[str]:
        """Recursively discover all site pages"""
        discovered_urls = set()
        
        if depth > self.max_depth:
            return []
        
        try:
            print(f"  Discovering from: {start_url} (depth {depth})")
            response = requests.get(start_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(start_url, href)
                
                # Normalize URL (remove fragments, trailing slashes)
                parsed = urlparse(full_url)
                normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
                
                if self.should_scrape_url(normalized_url):
                    discovered_urls.add(normalized_url)
        
        except Exception as e:
            print(f"    Discovery error: {e}")
        
        return list(discovered_urls)
    
    def extract_all_boutiques_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract all boutiques from nos-boutiques page"""
        boutiques = []
        seen_addresses = set()
        
        # Extraire tous les headings h3 (noms des boutiques)
        h3_tags = soup.find_all('h3')
        
        for h3 in h3_tags:
            # Trouver le texte suivant après le h3
            next_text = ""
            for sibling in h3.find_next_siblings(limit=10):
                text = sibling.get_text(strip=True)
                if text:
                    next_text += text + "\n"
                    # Arrêter si on trouve un téléphone (fin de section)
                    if re.search(r'0[1-9](?:[\s.]?\d{2}){4}', text):
                        break
            
            # Chercher adresse et téléphone dans le texte suivant
            addr_match = re.search(r'([\d]+\s+[Rr]ue[^-\n]+?-\s*75\d{3}\s+Paris)', next_text, re.IGNORECASE)
            tel_match = re.search(r'(0[1-9](?:[\s.]?\d{2}){4})', next_text)
            
            if addr_match and tel_match:
                name = h3.get_text(strip=True)
                adresse = addr_match.group(1).strip()
                telephone = tel_match.group(1).strip()
                
                # Éviter doublons
                if adresse in seen_addresses:
                    continue
                seen_addresses.add(adresse)
                
                # Extraire code postal
                cp_match = re.search(r'75(\d{3})', adresse)
                code_postal = f"75{cp_match.group(1)}" if cp_match else ""
                
                # Nettoyer nom (enlever "L'Arbre à Café -" si présent)
                if name.startswith("L'Arbre à Café"):
                    name = name
                else:
                    name = f"L'Arbre à Café - {name}"
                
                boutiques.append({
                    "name": name,
                    "telephone": telephone.replace('.', ' '),
                    "adresse": adresse,
                    "code_postal": code_postal,
                    "ville": "Paris",
                    "statut": "ouvert",
                    "url": "https://larbreacafe.com/pages/nos-boutiques"
                })
        
        return boutiques
    
    def is_boutique_page(self, url: str, soup: BeautifulSoup) -> bool:
        """Detect if page is a boutique page"""
        # Pattern matching on URL
        boutique_patterns = [
            '/boutique',
            '/nos-boutiques',
            '/content/'
        ]
        
        if any(pattern in url.lower() for pattern in boutique_patterns):
            return True
        
        # Check for Schema.org Restaurant/LocalBusiness type
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if '@graph' in data:
                        for item in data['@graph']:
                            item_type = item.get('@type', '').lower()
                            if 'restaurant' in item_type or 'localbusiness' in item_type:
                                return True
                    else:
                        item_type = data.get('@type', '').lower()
                        if 'restaurant' in item_type or 'localbusiness' in item_type:
                            return True
            except:
                continue
        
        # Check for boutique indicators in content
        text = soup.get_text().lower()
        indicators = ['horaires', 'adresse', 'tÃ©lÃ©phone', 'rÃ©server']
        matches = sum(1 for indicator in indicators if indicator in text)
        
        return matches >= 3
    
    def scrape_all_content(self):
        """Scrape all relevant site content dynamically"""
        print("\n" + "=" * 60)
        print("COMPLETE INDUSTRIAL SCRAPING - DYNAMIC DISCOVERY")
        print("=" * 60)
        
        # Start recursive discovery from base URL
        print(f"\n[1/2] Discovering all pages from {self.base_url}...")
        urls_to_process = [self.base_url]
        all_discovered = set()
        
        # Breadth-first crawling
        for depth in range(self.max_depth + 1):
            if not urls_to_process:
                break
            
            # Check max_pages limit if set
            if self.max_pages and len(self.visited_urls) >= self.max_pages:
                print(f"\n  Max pages limit reached ({self.max_pages})")
                break
            
            print(f"\n  Depth {depth}: {len(urls_to_process)} URLs to process")
            next_level_urls = []
            
            for url in urls_to_process:
                # Check again for max_pages in loop
                if self.max_pages and len(self.visited_urls) >= self.max_pages:
                    break
                    
                if url in all_discovered:
                    continue
                
                all_discovered.add(url)
                
                # Scrape page
                page_data = self.scrape_page(url)
                if page_data:
                    self.all_pages_content[url] = page_data
                    
                    # Check if it's a boutique page OR nos-boutiques page
                    try:
                        response = requests.get(url, headers=self.headers, timeout=15)
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # If it's nos-boutiques, extract all boutiques from content
                        if '/nos-boutiques' in url.lower():
                            print(f"    [NOS-BOUTIQUES PAGE] Extracting all boutiques...")
                            boutiques_extracted = self.extract_all_boutiques_from_page(soup)
                            self.boutiques.extend(boutiques_extracted)
                            print(f"    Extracted {len(boutiques_extracted)} boutiques")
                        elif self.is_boutique_page(url, soup):
                            print(f"    [BOUTIQUE DETECTED] {url}")
                            boutique_data = self.extract_boutique_data_from_soup(url, soup)
                            if boutique_data:
                                self.boutiques.append(boutique_data)
                    except:
                        pass
                
                # Discover new URLs from this page
                discovered = self.discover_pages(url, depth)
                next_level_urls.extend([u for u in discovered if u not in all_discovered])
                
                time.sleep(0.3)
            
            urls_to_process = list(set(next_level_urls))
        
        print(f"\n[2/2] Scraping complete!")
        print(f"  Total pages scraped: {len(self.all_pages_content)}")
        print(f"  Total boutiques found: {len(self.boutiques)}")
    
    def extract_boutique_data_from_soup(self, url: str, soup: BeautifulSoup) -> Dict:
        """Extract structured boutique data from already-loaded BeautifulSoup"""
        try:
            # Extract JSON-LD structured data
            json_ld_data = None
            scripts = soup.find_all('script', type='application/ld+json')
            
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if '@graph' in data:
                            for item in data['@graph']:
                                item_type = item.get('@type', '').lower()
                                if 'restaurant' in item_type or 'localbusiness' in item_type:
                                    json_ld_data = item
                                    break
                        else:
                            item_type = data.get('@type', '').lower()
                            if 'restaurant' in item_type or 'localbusiness' in item_type:
                                json_ld_data = data
                                
                    if json_ld_data:
                        break
                except (json.JSONDecodeError, KeyError):
                    continue
            
            # If no JSON-LD, fallback on HTML extraction
            if not json_ld_data:
                page_text = soup.get_text()
                h1 = soup.find('h1')
                
                # Extract phone
                telephone = ""
                tel_pattern = r'\+33\s?\d{1}\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}'
                tel_match = re.search(tel_pattern, page_text)
                if tel_match:
                    telephone = tel_match.group(0)
                
                # Extract address
                adresse = ""
                for string in soup.stripped_strings:
                    if re.search(r'\d+.*(?:Rue|Avenue|Boulevard|Place)', string, re.IGNORECASE):
                        adresse = string
                        break
                
                # Status
                statut = "ouvert"
                if "prochaine" in page_text.lower():
                    statut = "ouverture_prochaine"
                
                return {
                    "name": h1.get_text(strip=True) if h1 else "",
                    "telephone": telephone,
                    "adresse": adresse,
                    "statut": statut,
                    "url": url
                }
            
            # Extract from JSON-LD
            name = json_ld_data.get('name', '')
            telephone = json_ld_data.get('telephone', '')
            
            # Extract structured address
            address_data = json_ld_data.get('address', {})
            adresse = f"{address_data.get('streetAddress', '')}, {address_data.get('postalCode', '')} {address_data.get('addressLocality', '')}"
            
            # Extract and parse hours from openingHoursSpecification
            horaires = {}
            if 'openingHoursSpecification' in json_ld_data:
                horaires = self.parse_opening_hours(json_ld_data['openingHoursSpecification'])
            
            # Status
            page_text = soup.get_text()
            statut = "ouvert"
            if "prochaine" in page_text.lower():
                statut = "ouverture_prochaine"
            
            # Get coordinates
            coordinates = self.geocode_address(adresse)
            
            boutique_data = {
                "name": name,
                "telephone": telephone,
                "adresse": adresse,
                "horaires": horaires,
                "statut": statut,
                "url": url,
                "coordinates": coordinates,
                "description": f"Boutique {name}\nAdresse: {adresse}\nTÃ©lÃ©phone: {telephone}\n\nPour rÃ©server ou commander: <a href=\"{url}\" target=\"_blank\">Page de la boutique</a>"
            }
            
            return boutique_data
            
        except Exception as e:
            print(f"    Extraction error: {e}")
            return None
    
    def parse_produits_from_page(self, page_content: str) -> List[Dict]:
        """Parse page content to extract coffee products"""
        produits = []
        
        # Split by "COMMANDER" which separates each product
        product_blocks = page_content.split('COMMANDER')
        
        for block in product_blocks:
            block = block.strip()
            if not block or len(block) < 20:
                continue
            
            # Ignore navigation/system elements from the start
            skip_words = ['aller au contenu', 'gÃ©rer', 'accepter', 'refuser', 'cookies']
            if any(skip in block.lower() for skip in skip_words):
                continue
            
            # Clean: keep until "Plus" to separate name from rest
            # Format: "DISH NAME Plus description Plus traces..."
            parts = block.split('Plus')
            
            if not parts or len(parts[0].strip()) < 3:
                continue
            
            # Extract name (first part before "Plus")
            product_name = parts[0].strip()
            
            # If name contains multiple lines, take only first uppercase line
            name_lines = [l.strip() for l in product_name.split('\n') if l.strip()]
            if name_lines:
                # Keep first non-empty line as main name
                main_name = name_lines[0]
                
                # If name too long (> 150 chars), it's probably a badly split formula
                if len(main_name) > 150:
                    # Take until first lowercase word or punctuation
                    words = main_name.split()
                    clean_name_parts = []
                    for word in words:
                        if word.isupper() or word[0].isupper():
                            clean_name_parts.append(word)
                        else:
                            break
                    main_name = ' '.join(clean_name_parts) if clean_name_parts else words[0]
                
                product_name = main_name
            
            # Extract description (second part after first "Plus")
            description = parts[1].strip() if len(parts) > 1 else ''
            
            # Find price (â‚¬ pattern)
            price_match = re.search(r'(\d+[,.]?\d*)\s*â‚¬', block)
            price = price_match.group(0) if price_match else ''
            
            # Detect tags (vegetarian, spicy, etc.)
            tags = []
            if 'vÃ©gÃ©' in block.lower() or 'vÃ©gÃ©tarien' in block.lower():
                tags.append('vegetarien')
            if 'Ã©picÃ©' in block.lower() or 'piment' in block.lower():
                tags.append('epice')
            if 'signature' in block.lower() or 'grand cru' in block.lower():
                tags.append('signature')
            
            produits.append({
                'nom': product_name,
                'description': description[:300],  # Limit length
                'prix': price,
                'tags': tags,
                'raw_content': block[:500]  # Keep raw content for RAG
            })
        
        return produits
    
    def extract_boutique_data(self, url: str) -> Dict:
        """Extract structured boutique data from URL (fetches page)"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            return self.extract_boutique_data_from_soup(url, soup)
        except Exception as e:
            print(f"    Error fetching {url}: {e}")
            return None
    
    def geocode_address(self, address: str) -> Dict:
        """Get coordinates from address using Nominatim (OpenStreetMap)"""
        if address in self.geocoding_cache:
            return self.geocoding_cache[address]
        
        try:
            # Clean address for better results
            clean_address = address.replace('\n', ', ').strip()
            url = f"https://nominatim.openstreetmap.org/search"
            params = {
                'q': clean_address,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'fr'  # France only
            }
            
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if data:
                coords = {
                    'lat': float(data[0]['lat']),
                    'lon': float(data[0]['lon'])
                }
                self.geocoding_cache[address] = coords
                time.sleep(1)  # Nominatim rate limit: 1 req/sec
                return coords
            
        except Exception as e:
            print(f"    Geocoding error: {e}")
        
        return None
    
    def parse_opening_hours(self, specs: List[Dict]) -> Dict:
        """Parse openingHoursSpecification from Schema.org
        
        This site uses validFrom/validThrough format without dayOfWeek.
        We group identical time ranges.
        """
        if not specs:
            return {}
        
        # Collect all unique time ranges
        time_ranges = []
        for spec in specs:
            opens = spec.get('opens', '')
            closes = spec.get('closes', '')
            
            if opens and closes:
                time_range = f"{opens}-{closes}"
                if time_range not in time_ranges:
                    time_ranges.append(time_range)
        
        # If we have time ranges, apply to all days
        # (site doesn't specify individual days in openingHoursSpecification)
        if time_ranges:
            combined = ", ".join(time_ranges)
            return {
                "lundi": combined,
                "mardi": combined,
                "mercredi": combined,
                "jeudi": combined,
                "vendredi": combined,
                "samedi": combined,
                "dimanche": combined
            }
        
        return {}
    
    def save_complete_knowledge_base(self):
        """Save complete knowledge base"""
        
        # Organize pages by category
        categorized_pages = {
            'produits': [],
            'boutiques': [],
            'fidelite': [],
            'service_client': [],
            'concept': [],
            'autres': []
        }
        
        for url, content in self.all_pages_content.items():
            if '/la-carte/' in url or '/nos-cafes/' in url:
                # Parse products from page
                products = self.parse_produits_from_page(content['content'])
                # Create document per product
                for product in products:
                    categorized_pages['produits'].append({
                        'url': url,
                        'title': f"Produit: {product['nom']}",
                        'content': f"{product['nom']}\n{product['description']}\nPrix: {product['prix']}\nTags: {', '.join(product['tags'])}\n\nPour commander: <a href=\"{url}\" target=\"_blank\">Boutique en ligne</a>\n\n{product['raw_content']}",
                        'product_data': product
                    })
            elif '/fidelite/' in url or 'fidÃ©litÃ©' in content['title'].lower():
                content['content'] = f"{content['content']}\n\nPour en savoir plus: <a href=\"{url}\" target=\"_blank\">Programme de fidÃ©litÃ©</a>"
                categorized_pages['fidelite'].append(content)
            elif '/service-client/' in url or 'faq' in url.lower():
                content['content'] = f"{content['content']}\n\nContactez-nous: <a href=\"{url}\" target=\"_blank\">Service client</a>"
                categorized_pages['service_client'].append(content)
            elif '/notre-concept/' in url or '/nos-engagements/' in url:
                content['content'] = f"{content['content']}\n\nDÃ©couvrez-en plus: <a href=\"{url}\" target=\"_blank\">Notre concept</a>"
                categorized_pages['concept'].append(content)
            elif '/devenir-franchise/' in url:
                content['content'] = f"{content['content']}\n\nRejoignez notre rÃ©seau: <a href=\"{url}\" target=\"_blank\">Devenir franchisÃ©</a>"
                categorized_pages['autres'].append(content)
            elif '/nous-rejoindre/' in url:
                content['content'] = f"{content['content']}\n\nPostulez maintenant: <a href=\"{url}\" target=\"_blank\">Nous rejoindre</a>"
                categorized_pages['autres'].append(content)
            elif '/service-traiteur/' in url:
                content['content'] = f"{content['content']}\n\nDemandez un devis: <a href=\"{url}\" target=\"_blank\">Service traiteur</a>"
                categorized_pages['autres'].append(content)
            elif '/nos-boutiques/' in url:
                content['content'] = f"{content['content']}\n\nTrouvez votre boutique: <a href=\"{url}\" target=\"_blank\">Nos boutiques</a>"
                categorized_pages['autres'].append(content)
            else:
                content['content'] = f"{content['content']}\n\nPlus d'infos: <a href=\"{url}\" target=\"_blank\">En savoir plus</a>"
                categorized_pages['autres'].append(content)
        
        data = {
            "version": "4.0_industrial",
            "date_scraping": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_pages_scrapees": len(self.all_pages_content),
            "total_boutiques": len(self.boutiques),
            "boutiques": self.boutiques,
            "pages_par_categorie": categorized_pages,
            "informations_generales": {
                "concept": "CafÃ© de SpÃ©cialitÃ© - TorrÃ©facteur Artisanal depuis 2009",
                "programme_fidelite": "1â‚¬ dÃ©pensÃ© = 1 grain de riz (point)",
                "reduction_premiere_commande": "-10% avec code larbrecaf10",
                "services_disponibles": ["Sur place", "Ã€ emporter", "Livraison", "Drive"],
                "reseaux_sociaux": {
                    "instagram": "https://www.instagram.com/larbrecaf/",
                    "facebook": "https://www.facebook.com/larbrecafParis/",
                    "tiktok": "https://www.tiktok.com/@larbrecaf"
                }
            }
        }
        
        filename = "larbrecaf_knowledge_industrial_2025.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 60)
        print("SCRAPING COMPLETE")
        print("=" * 60)
        print(f"\nFile: {filename}")
        print(f"  Scraped pages: {len(self.all_pages_content)}")
        print(f"  Boutiques: {len(self.boutiques)}")
        print(f"  Produits: {len(categorized_pages['produits'])} pages")
        print(f"  Fidelity: {len(categorized_pages['fidelite'])} pages")
        print(f"  Customer service: {len(categorized_pages['service_client'])} pages")
        print(f"  Concept: {len(categorized_pages['concept'])} pages")
        print(f"  Other: {len(categorized_pages['autres'])} pages")
        
        return filename

def main():
    print("=" * 60)
    print("L''ARBRE À CAFÉ INDUSTRIAL SCRAPER 2025")
    print("100% Dynamic - No Hardcoded URLs")
    print("=" * 60)
    
    scraper = larbrecafIndustrialScraper()
    scraper.scrape_all_content()
    filename = scraper.save_complete_knowledge_base()
    
    print("\nComplete knowledge base ready!")
    print(f"File: {filename}")

if __name__ == "__main__":
    main()
