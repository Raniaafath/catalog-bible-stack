#!/bin/bash
# Script de déploiement du frontend
# Copie le contenu de frontend/dist/ vers /srv/www/bib.neomarkgroup.fr/

set -e  # Arrêter en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Déploiement du frontend ===${NC}"

# Vérifier qu'on est dans le bon répertoire
if [ ! -d "frontend" ]; then
    echo -e "${RED}Erreur: Le dossier 'frontend' n'existe pas.${NC}"
    echo "Assurez-vous d'exécuter ce script depuis la racine du projet Django."
    exit 1
fi

# Aller dans le dossier frontend
cd frontend

# Vérifier que node_modules existe, sinon installer les dépendances
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installation des dépendances npm...${NC}"
    npm install
fi

# Construire le frontend
echo -e "${YELLOW}Construction du frontend (npm run build)...${NC}"
npm run build

# Vérifier que le dossier dist existe
if [ ! -d "dist" ]; then
    echo -e "${RED}Erreur: Le dossier 'dist' n'a pas été créé après le build.${NC}"
    exit 1
fi

# Retourner à la racine
cd ..

# Déployer avec rsync
echo -e "${YELLOW}Déploiement vers /srv/www/bib.neomarkgroup.fr/...${NC}"
rsync -av --delete \
    --exclude='.git' \
    --exclude='.DS_Store' \
    frontend/dist/ \
    /srv/www/bib.neomarkgroup.fr/

echo -e "${GREEN}✓ Déploiement terminé avec succès!${NC}"
echo -e "${GREEN}Le frontend est maintenant disponible sur https://bib.neomarkgroup.fr${NC}"
