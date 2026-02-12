Business Architecture

Objectif : Définir pour qui et pourquoi vous construisez ce système.

L'objectif du LLM Task Manager est de créer un écosystème de gestion de projet où la barrière entre la conception (le dialogue avec l'IA) et l'exécution (le ticket de tâche) disparaît. Il ne s'agit pas de forcer une IA à remplir un formulaire humain, mais de lui donner les outils pour structurer le travail de manière autonome.

Persona,Profil,Contexte & Besoins,Frustrations

1. LEA "Tech Lead",
Responsable de la qualité et de la roadmap.
"Doit s'assurer que les tickets sont clairs, bien estimés et que les décisions techniques sont documentées."
    -> "Perdre 1h par jour à traduire des discussions Slack en tickets Jira est épuisant et n'apporte aucune valeur technique.

2. Sarah, "PO",
Responsable de la vision produit et des priorités métier.
Doit transformer des besoins clients flous en spécifications claires (Epics/Stories) et suivre l'avancement global sans harceler les développeurs.
    -> "Jira est un trou noir. Je passe mon temps à demander 'où ça en est ?' parce que les tickets ne sont jamais à jour, et rédiger des Stories détaillées me prend un temps infini."

Job To Be Done (JTBD)

    En tant que Tech Lead, je veux déléguer la structuration technique et administrative de mon projet à un agent IA via MCP, afin de me concentrer sur l'architecture et le code tout en maintenant un backlog parfaitement à jour.

Cas d'usage concrets

    Extraction de Story en temps réel : Léa discute d'une nouvelle fonctionnalité de sécurité avec l'IA dans son IDE. Sans quitter le chat, l'IA identifie les tâches nécessaires et appelle le tool create_story pour les ajouter au backlog.

    Génération de Documentation Technique : Suite à une séance de debugging complexe, Léa demande à l'IA de résumer la solution. L'IA utilise le tool create_document avec le template Technical Decision Record (TDR) pour consigner la décision dans le projet.

    Maintenance autonome du Sprint : En fin de journée, l'IA analyse les Stories dont le statut est resté bloqué en in_progress. Elle ajoute un commentaire sur chaque story pour demander un statut ou propose de les reporter au sprint suivant via update_story_sprint.

Règles métier du domaine (Business Rules)

Le système garantit l'intégrité des données via des règles strictes appliquées aux interfaces REST et MCP :

    BR-01 (Estimation Fibonacci) : Les estimations (story_points) doivent obligatoirement appartenir à la suite de Fibonacci : 0, 1, 2, 3, 5, 8, 13. (poids des stories)

    BR-02 (Workflow de statut) : Une story doit respecter l'ordre suivant : backlog → todo → in_progress → in_review → done. Aucun saut d'étape n'est autorisé.

    BR-03 (Unicité du Sprint Actif) : Une story ne peut être affectée qu'à un seul sprint actif à la fois. L'affectation à un nouveau sprint retire automatiquement la story du sprint précédent.

    BR-04 (Condition de clôture) : Un sprint ne peut être clôturé (closed) que si 100% de ses stories sont à l'état done. Les stories restantes doivent être déplacées avant la clôture.


---

## 3.2 **Architecture Suggérée**

### **1. SERVICES (Microservices/Modules)**

#### **Services Cœur**

**A. Service de Gestion des Stories**
- **Responsabilités :**
  - Opérations CRUD sur les Stories
  - Estimation en story points (validation Fibonacci - BR-01)
  - Application du workflow de statuts (BR-02)
  - Logique d'assignation aux sprints (BR-03)
- **Opérations clés :**
  - `create_story()`
  - `update_story()`
  - `update_story_status()`
  - `update_story_sprint()`
  - `list_stories()`

**B. Service de Gestion des Sprints**
- **Responsabilités :**
  - Cycle de vie des sprints (création, activation, clôture)
  - Validation de clôture (BR-04 : toutes les stories doivent être done)
  - Gestion de l'association Story-Sprint
- **Opérations clés :**
  - `create_sprint()`
  - `activate_sprint()`
  - `close_sprint()`
  - `get_sprint_status()`

**C. Service de Gestion des Tickets**
- **Responsabilités :**
  - Opérations CRUD sur les tickets individuels
  - Déplacement de tickets entre sprints/colonnes
  - Assignation et réassignation de tickets
  - Gestion des dépendances entre tickets
  -Archivage et suppression de tickets
  - Historique des modifications
- **Opérations clés :**
  - `create_ticket(title, description, assignee, priority)`
  - `update_ticket(id, fields)`
  - `move_ticket(id, target_status)` → Valide transitions BR-02
  - `assign_ticket(id, user_id)`
  - `delete_ticket(id)` → Soft delete avec archivage
  - `restore_ticket(id)` → Restauration depuis archive
  - `link_tickets(parent_id, child_id)` → Gestion dépendances
  - `get_ticket_history(id)` → Audit trail complet
  - `search_tickets(filters)` → Recherche avancée
- **Règles spécifiques :**
  - Un ticket ne peut être supprimé que s'il est en statut `backlog` ou `todo`
  - Le déplacement entre sprints nécessite validation BR-03
  - L'historique est immuable (event sourcing)

**D. Service de Documentation**
- **Responsabilités :**
  - Génération de documents basés sur templates (TDR, ADR, etc.)
  - Versioning et stockage des documents
  - Liaison documents-Stories/Sprints
- **Opérations clés :**
  - `create_document(template, context)`
  - `list_templates()`
  - `attach_document_to_story()`

**E. Moteur de Règles Métier**
- **Responsabilités :**
  - Validation centralisée des règles BR-01 à BR-04
  - Machine à états pour le workflow des stories et tickets
  - Application des politiques
- **Validations :**
  - Validateur Fibonacci
  - Validateur de transitions de statut
  - Validateur d'assignation aux sprints
  - Validateur de clôture de sprint
  - Validateur de suppression de tickets

---

