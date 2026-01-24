#!/usr/bin/env python3
"""Simulation complète du chatbot L'Arbre à Café"""

import requests
import json
from datetime import datetime
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import re

def add_hyperlink(paragraph, url, text):
    """Ajoute un hyperlien cliquable dans un paragraphe"""
    # Créer une relation d'hyperlien
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    
    # Créer l'élément hyperlink
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)
    
    # Créer un nouveau run pour le texte du lien
    new_run = OxmlElement('w:r')
    
    # Propriétés du run (style lien)
    rPr = OxmlElement('w:rPr')
    
    # Couleur bleue
    color = OxmlElement('w:color')
    color.set(qn('w:val'), '0563C1')
    rPr.append(color)
    
    # Souligné
    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(u)
    
    # Police Calibri 11
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), 'Calibri')
    rFonts.set(qn('w:hAnsi'), 'Calibri')
    rPr.append(rFonts)
    
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), '22')  # 11pt = 22 half-points
    rPr.append(sz)
    
    new_run.append(rPr)
    
    # Ajouter le texte
    new_run.text = text
    hyperlink.append(new_run)
    
    paragraph._p.append(hyperlink)
    return hyperlink

def run_simulation():
    questions = [
        'Proposez-vous des cafés de la ferme Mariposa ?',
        'Quel est le prix du café Source en 250g ?',
        'Avez-vous une boutique dans le 9ème arrondissement ?',
        'Combien de boutiques avez-vous à Paris ?',
        'Proposez-vous des formations pour devenir barista ?',
        'Vendez-vous des machines Sage The Barista Pro ?',
        'Proposez-vous des cafés biodynamiques ?',
        'Avez-vous des cafés d\'Éthiopie ?',
        'Quels sont vos cafés d\'exception ?',
        'Comment contacter la boutique Paris 09 ?'
    ]
    
    results = []
    
    print('\n' + '='*70)
    print('   SIMULATION CHATBOT L\'ARBRE À CAFÉ - AGENTIC RAG')
    print(f'   Date: {datetime.now().strftime("%d/%m/%Y %H:%M")}')
    print('='*70)
    
    for i, q in enumerate(questions, 1):
        print(f'\n[Q{i}] {q}')
        print('-'*70)
        try:
            r = requests.post('http://localhost:8002/chat', 
                            json={'message': q}, 
                            timeout=30)
            response = r.json().get('response', 'Erreur')
            print(response)
            results.append({
                'numero': i,
                'question': q, 
                'response': response,
                'status': 'ok'
            })
        except Exception as e:
            error_msg = f'ERREUR: {str(e)}'
            print(error_msg)
            results.append({
                'numero': i,
                'question': q, 
                'response': error_msg,
                'status': 'error'
            })
    
    # Sauvegarder en JSON avec timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    json_filename = f'simulation_results_{timestamp}.json'
    output_data = {
        'date': datetime.now().isoformat(),
        'company': 'L\'Arbre à Café',
        'total_questions': len(questions),
        'questions': results
    }
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Export DOCX
    docx_filename = f'simulation_results_{timestamp}.docx'
    doc = Document()
    
    # Titre principal - centré et souligné
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(f"Agent intelligent pour L'Arbre à Café - Simulation du {datetime.now().strftime('%d/%m/%Y')}")
    run.font.name = 'Calibri'
    run.font.size = Pt(11)
    run.underline = True
    
    doc.add_paragraph()  # Ligne vide
    
    # Ajouter chaque question/réponse
    for r in results:
        # Question
        question_para = doc.add_paragraph()
        question_run = question_para.add_run(f"Q{r['numero']} : {r['question']}")
        question_run.font.name = 'Calibri'
        question_run.font.size = Pt(11)
        
        doc.add_paragraph()  # Ligne vide
        
        # Réponse - traiter les liens HTML
        response_text = r['response']
        response_para = doc.add_paragraph()
        
        # Parser et ajouter texte avec hyperliens
        # Pattern pour extraire les liens: <a href="URL" target="_blank">Texte</a>
        link_pattern = r'<a href="([^"]+)"[^>]*>([^<]+)</a>'
        last_pos = 0
        
        for match in re.finditer(link_pattern, response_text):
            # Texte avant le lien
            before_text = response_text[last_pos:match.start()]
            if before_text:
                run = response_para.add_run(before_text)
                run.font.name = 'Calibri'
                run.font.size = Pt(11)
            
            # Ajouter le lien cliquable avec la fonction add_hyperlink
            url = match.group(1)
            link_text = match.group(2)
            add_hyperlink(response_para, url, link_text)
            
            last_pos = match.end()
        
        # Texte après le dernier lien
        remaining_text = response_text[last_pos:]
        if remaining_text:
            # Nettoyer les balises restantes
            remaining_text = re.sub(r'<[^>]+>', '', remaining_text)
            run = response_para.add_run(remaining_text)
            run.font.name = 'Calibri'
            run.font.size = Pt(11)
        
        doc.add_paragraph()  # Ligne vide
        
        # Séparateur
        separator = doc.add_paragraph('---')
        sep_run = separator.runs[0]
        sep_run.font.name = 'Calibri'
        sep_run.font.size = Pt(11)
        
        doc.add_paragraph()  # Ligne vide
    
    doc.save(docx_filename)
    
    print('\n' + '='*70)
    print(f'[OK] JSON: {json_filename}')
    print(f'[OK] DOCX: {docx_filename}')
    print('='*70)
    
    return results

if __name__ == "__main__":
    run_simulation()
