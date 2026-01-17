#!/usr/bin/env python3
"""
Validation des réponses du chatbot contre la source de vérité
Compare chaque réponse avec les données du JSON industriel
"""

import json
import re

def load_knowledge_base():
    with open('terresdecafe_knowledge_industrial_2025.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def load_simulation_results():
    with open('simulation_results.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_responses():
    kb = load_knowledge_base()
    results = load_simulation_results()
    
    validations = []
    
    print("\n" + "="*80)
    print("VALIDATION DES RÉPONSES - COMPARAISON AVEC SOURCE DE VÉRITÉ")
    print("="*80 + "\n")
    
    # Validation Q1 - Récompenses 2024
    q1 = results['questions'][0]
    print(f"[Q1] {q1['question']}")
    awards_in_response = [
        'Outstanding Achievement Award' in q1['response'],
        'Meilleur Expresso' in q1['response'],
        'Champion du Monde Ibrik' in q1['response']
    ]
    # Chercher dans le KB
    kb_content = json.dumps(kb)
    awards_in_kb = [
        'Outstanding Achievement Award' in kb_content,
        'Meilleur Expresso de France 2024' in kb_content,
        'Champion du Monde Ibrik' in kb_content
    ]
    q1_valid = all(awards_in_kb) and all(awards_in_response)
    status1 = "✅ VALIDE" if q1_valid else "❌ INVALIDE"
    print(f"{status1} - Récompenses trouvées dans KB: {sum(awards_in_kb)}/3")
    validations.append({'question': 1, 'valid': q1_valid, 'details': f'{sum(awards_in_kb)}/3 récompenses vérifiées'})
    
    # Validation Q2 - Score 80+
    q2 = results['questions'][1]
    print(f"\n[Q2] {q2['question']}")
    score80_valid = (
        'Specialty Coffee Association' in q2['response'] and
        '80' in q2['response'] and
        'SCA' in q2['response']
    )
    status2 = "✅ VALIDE" if score80_valid else "❌ INVALIDE"
    print(f"{status2} - Définition SCA présente")
    validations.append({'question': 2, 'valid': score80_valid, 'details': 'Définition SCA correcte'})
    
    # Validation Q3 - Expresso vs Filtre
    q3 = results['questions'][2]
    print(f"\n[Q3] {q3['question']}")
    expresso_valid = (
        'pression' in q3['response'].lower() and
        'filtre' in q3['response'].lower()
    )
    status3 = "✅ VALIDE" if expresso_valid else "❌ INVALIDE"
    print(f"{status3} - Différence méthodes expliquée")
    validations.append({'question': 3, 'valid': expresso_valid, 'details': 'Méthodes de préparation expliquées'})
    
    # Validation Q4 - Livraison 50€
    q4 = results['questions'][3]
    print(f"\n[Q4] {q4['question']}")
    livraison_valid = '50' in q4['response'] and 'point relais' in q4['response'].lower()
    livraison_in_kb = 'Livraison offerte en point relais à partir de 50€' in kb_content
    status4 = "✅ VALIDE" if (livraison_valid and livraison_in_kb) else "❌ INVALIDE"
    print(f"{status4} - Livraison 50€ confirmée dans KB")
    validations.append({'question': 4, 'valid': livraison_valid and livraison_in_kb, 'details': 'Montant exact 50€'})
    
    # Validation Q5 - Fondateur Christophe Servell 2009
    q5 = results['questions'][4]
    print(f"\n[Q5] {q5['question']}")
    fondateur_valid = (
        'Christophe Servell' in q5['response'] and
        '2009' in q5['response']
    )
    fondateur_in_kb = 'Christophe Servell' in kb_content and '2009' in kb_content
    status5 = "✅ VALIDE" if (fondateur_valid and fondateur_in_kb) else "❌ INVALIDE"
    print(f"{status5} - Fondateur et date confirmés dans KB")
    validations.append({'question': 5, 'valid': fondateur_valid and fondateur_in_kb, 'details': 'Christophe Servell, 2009'})
    
    # Validation Q6 - Torréfaction Île-de-France Loring
    q6 = results['questions'][5]
    print(f"\n[Q6] {q6['question']}")
    torrefaction_valid = (
        'Île-de-France' in q6['response'] or 'Ile-de-France' in q6['response']
    ) and 'Loring' in q6['response']
    torrefaction_in_kb = 'Loring' in kb_content
    status6 = "✅ VALIDE" if (torrefaction_valid and torrefaction_in_kb) else "❌ INVALIDE"
    print(f"{status6} - Torréfacteurs Loring confirmés dans KB")
    validations.append({'question': 6, 'valid': torrefaction_valid and torrefaction_in_kb, 'details': 'Loring Île-de-France'})
    
    # Validation Q7 - Adresse Blancs-Manteaux
    q7 = results['questions'][6]
    print(f"\n[Q7] {q7['question']}")
    blancs_manteaux_data = next((b for b in kb['boutiques'] if 'Blancs Manteaux' in b['name']), None)
    adresse_valid = False
    if blancs_manteaux_data:
        adresse_kb = blancs_manteaux_data['adresse']
        tel_kb = blancs_manteaux_data['telephone']
        adresse_valid = (
            '36 rue des Blancs Manteaux' in q7['response'] and
            '09 87 02 51 76' in q7['response']
        )
    status7 = "✅ VALIDE" if adresse_valid else "❌ INVALIDE"
    print(f"{status7} - Adresse: {blancs_manteaux_data['adresse'] if blancs_manteaux_data else 'N/A'}")
    print(f"         Tel: {blancs_manteaux_data['telephone'] if blancs_manteaux_data else 'N/A'}")
    validations.append({'question': 7, 'valid': adresse_valid, 'details': f'Adresse et téléphone vérifiés'})
    
    # Validation Q8 - Horaires Versailles
    q8 = results['questions'][7]
    print(f"\n[Q8] {q8['question']}")
    versailles_data = next((b for b in kb['boutiques'] if 'Versailles' in b['name']), None)
    horaires_valid = False
    if versailles_data:
        horaires_valid = (
            '10h' in q8['response'] and
            '18h30' in q8['response']
        )
    status8 = "✅ VALIDE" if horaires_valid else "❌ INVALIDE"
    print(f"{status8} - Horaires: {versailles_data['horaires'] if versailles_data else 'N/A'}")
    validations.append({'question': 8, 'valid': horaires_valid, 'details': 'Horaires corrects'})
    
    # Validation Q9 - Nombre de boutiques ⚠️ CRITIQUE
    q9 = results['questions'][8]
    print(f"\n[Q9] {q9['question']}")
    nb_boutiques_kb = kb['total_boutiques']
    nb_boutiques_response = None
    match = re.search(r'(\d+)\s+boutiques?', q9['response'])
    if match:
        nb_boutiques_response = int(match.group(1))
    boutiques_valid = nb_boutiques_response == nb_boutiques_kb
    status9 = "❌ ERREUR CRITIQUE" if not boutiques_valid else "✅ VALIDE"
    print(f"{status9} - KB dit: {nb_boutiques_kb} | Réponse dit: {nb_boutiques_response}")
    if not boutiques_valid:
        print(f"         ⚠️ HALLUCINATION DÉTECTÉE: Le chatbot a inventé le nombre de boutiques")
    validations.append({'question': 9, 'valid': boutiques_valid, 'details': f'KB={nb_boutiques_kb}, Réponse={nb_boutiques_response}'})
    
    # Validation Q10 - Meilleur café
    q10 = results['questions'][9]
    print(f"\n[Q10] {q10['question']}")
    # Vérifier si le café mentionné existe dans le KB
    cafe_valid = 'Las Brujas' in kb_content or 'Pacamara' in kb_content
    status10 = "✅ VALIDE" if cafe_valid else "⚠️ À VÉRIFIER"
    print(f"{status10} - Café mentionné trouvé dans KB")
    validations.append({'question': 10, 'valid': cafe_valid, 'details': 'Café Las Brujas dans KB'})
    
    # Résumé
    print("\n" + "="*80)
    print("RÉSUMÉ VALIDATION")
    print("="*80)
    total_valid = sum(1 for v in validations if v['valid'])
    total = len(validations)
    print(f"\n✅ Réponses valides: {total_valid}/{total}")
    print(f"❌ Réponses invalides: {total - total_valid}/{total}")
    
    if total - total_valid > 0:
        print("\n⚠️ PROBLÈMES DÉTECTÉS:")
        for v in validations:
            if not v['valid']:
                print(f"  • Q{v['question']}: {v['details']}")
    
    print("\n" + "="*80)
    
    return validations

if __name__ == "__main__":
    validate_responses()
