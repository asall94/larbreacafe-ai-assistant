#!/usr/bin/env python3
"""Simulation complète du chatbot L'Arbre à Café"""

import requests
import json
from datetime import datetime

def run_simulation():
    questions = [
        'Avez-vous des cafés de votre ferme Mariposa ?',
        'Quelle est l\'adresse de votre boutique Rue du Nil ?',
        'Proposez-vous des formations pour devenir barista ?',
        'Quels sont vos horaires d\'ouverture à Paris 7 ?',
        'Avez-vous une boutique dans le 9ème arrondissement ?',
        'Combien de boutiques avez-vous à Paris ?',
        'Vendez-vous des machines Sage The Barista Pro ?',
        'Proposez-vous des cafés biodynamiques ?',
        'Avez-vous des cafés d\'Éthiopie ?',
        'Quels sont vos cafés d\'exception ?'
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
    json_filename = f'simulation_results_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    output_data = {
        'date': datetime.now().isoformat(),
        'company': 'L\'Arbre à Café',
        'total_questions': len(questions),
        'questions': results
    }
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Export Markdown
    md_filename = f'simulation_results_{datetime.now().strftime("%Y%m%d_%H%M")}.md'
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write(f'# Simulation Chatbot L\'Arbre à Café\n\n')
        f.write(f'**Date:** {datetime.now().strftime("%d/%m/%Y %H:%M")}\n\n')
        f.write(f'**Total questions:** {len(questions)}\n\n')
        f.write('---\n\n')
        
        for r in results:
            f.write(f'## Q{r["numero"]}: {r["question"]}\n\n')
            if r['status'] == 'ok':
                f.write(f'{r["response"]}\n\n')
            else:
                f.write(f'**ERREUR:** {r["response"]}\n\n')
            f.write('---\n\n')
    
    print('\n' + '='*70)
    print(f'[OK] JSON: {json_filename}')
    print(f'[OK] Markdown: {md_filename}')
    print('='*70)
    
    return results

if __name__ == "__main__":
    run_simulation()
