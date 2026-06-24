# Pourquoi BountyOps existe

## Pitch en une phrase

BountyOps est un agent autonome qui trouve des opportunités payantes, estime si elles valent le coup, lance des agents spécialisés, vérifie les livrables, et produit un dossier de soumission prêt à envoyer.

## Le problème

Un builder peut gagner de l'argent avec des hackathons, bounties, grants, appels à projets, concours IA ou programmes web3.

Mais ces opportunités sont dispersées partout.

Il faut répondre manuellement à beaucoup de questions :

- Est-ce que cette opportunité vaut mon temps ?
- Est-ce que le prize est assez gros ?
- Est-ce qu'il y a beaucoup de concurrence ?
- Est-ce que mes compétences correspondent ?
- Qu'est-ce que je dois construire ?
- Qu'est-ce que je dois soumettre ?
- Est-ce que je peux faire une bonne démo avant la deadline ?

Beaucoup de builders perdent du temps soit parce qu'ils ratent les bonnes opportunités, soit parce qu'ils travaillent sur des opportunités peu rentables.

## L'idée simple

BountyOps aide un builder à décider où investir son temps.

Il ne fait pas seulement une liste d'opportunités. Il transforme une opportunité en plan d'exécution.

À partir d'une opportunité payante, BountyOps :

1. extrait les informations importantes ;
2. estime l'expected value ;
3. recommande GO, MAYBE ou NO_GO ;
4. propose le meilleur angle de projet ;
5. lance des agents spécialisés pour préparer la soumission ;
6. vérifie le livrable final ;
7. retourne un proof hash et un ledger de commandes.

## Pourquoi c'est adapté à CROO

CROO veut montrer une économie où les agents peuvent se découvrir, s'appeler, se payer et vérifier le travail livré.

BountyOps démontre exactement ça.

BountyOps agit comme un agent acheteur / orchestrateur. Il ne fait pas tout seul. Il embauche plusieurs agents spécialisés :

- OpportunityScoutAgent
- ROIScorerAgent
- AgentDesignerAgent
- SubmissionWriterAgent
- VerifierAgent

Chaque agent fait une partie du travail. BountyOps les paie, récupère leurs livrables, vérifie le résultat, puis assemble le dossier final.

## Le workflow A2A

Buyer Agent
→ BountyOps
→ OpportunityScoutAgent
→ ROIScorerAgent
→ AgentDesignerAgent
→ SubmissionWriterAgent
→ VerifierAgent
→ Final Submission Pack + Proof Hash

Ce n'est pas juste un chatbot. C'est un workflow de commerce entre agents.

## Ce que BountyOps produit

Pour chaque opportunité, BountyOps retourne :

- décision GO / MAYBE / NO_GO ;
- score d'expected value ;
- projet recommandé ;
- tracks recommandés ;
- rationale ;
- README outline ;
- draft de writeup DoraHacks ;
- script vidéo ;
- checklist de soumission ;
- ledger des ordres agents ;
- proof hash.

## Mode mock vs mode CROO live

BountyOps a deux modes.

CAP_MODE=mock est le mode local déterministe utilisé pour les tests et les démos reproductibles.

CAP_MODE=live est le chemin d'intégration live avec le SDK CROO, les vrais agents, les vrais ordres, les vrais wallets et les vrais livrables.

Le mode mock ne doit jamais être présenté comme un vrai settlement CROO. Il sert à montrer le comportement du système sans dépendre des credentials.

## Ce qu'il faut pour une exécution CROO 100% live

Pour faire tourner BountyOps entièrement en live sur CROO, il faut :

- une listing CROO Agent Store ;
- les credentials SDK CROO ;
- un wallet agent ;
- au moins un buyer wallet réel ;
- des agents contreparties ;
- des ordres réels ou testnet ;
- une livraison via CROO CAP.

Le repo est conçu pour ajouter cette couche live sans changer la logique produit.

## Pourquoi le projet peut gagner

BountyOps colle aux critères CROO :

- Technical execution : API, tests, adapter CAP, ledger, proof hash.
- A2A composability : plusieurs agents spécialisés sont appelés et payés.
- Innovation : l'agent transforme la recherche d'opportunités en commerce agent-to-agent.
- Usability : les builders peuvent l'utiliser pour trouver et préparer des opportunités rentables.
- Presentation : le hackathon CROO lui-même sert de cas de démo réel.

## Pourquoi ça sert même hors hackathon

Même si le hackathon se termine, le produit reste utile.

BountyOps peut servir pour :

- compétitions Kaggle ;
- hackathons DoraHacks ;
- hackathons Devpost ;
- grants Gitcoin ;
- bounties web3 ;
- programmes startup IA ;
- grants de recherche ;
- RFPs ;
- concours techniques.

Le produit long terme est simple :

Trouver où un builder peut gagner de l'argent, puis préparer la meilleure soumission possible.
