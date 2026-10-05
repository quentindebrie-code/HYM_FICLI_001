# Déploiement alternatif (hors Streamlit Cloud)

À utiliser si Streamlit Cloud ne démarre pas l'application. Le code est
inchangé : seule la manière de l'héberger change. Les données restent dans
Supabase (PostgreSQL), donc rien n'est perdu en changeant d'hébergeur.

## Ce dont l'application a besoin

| Variable d'environnement | Rôle | Obligatoire |
|---|---|---|
| `HYMPYR_DATABASE_URL` | URL PostgreSQL Supabase (**Session pooler**, port 5432) | Oui en production |
| `PORT` | Port d'écoute, fourni par l'hébergeur | Selon l'hébergeur |

Sans `HYMPYR_DATABASE_URL`, l'application bascule en SQLite sur disque
éphémère : les données sont perdues au redémarrage. Ne l'utiliser que pour un
essai.

Les mots de passe utilisent les empreintes inscrites dans `app.py`, car
`[motsdepasse]` n'est lu que depuis `st.secrets` (fichier secrets de Streamlit).
Pour les changer sans Streamlit Cloud, modifier `PROFILS` dans `app.py`.

## Déploiement type (hébergeur avec Dockerfile)

1. Créer un service web **depuis ce dépôt**, branche choisie, avec le
   `Dockerfile` à la racine.
2. Région **Union européenne** (données clients classées C2).
3. Renseigner `HYMPYR_DATABASE_URL` dans les variables secrètes de l'hébergeur,
   jamais dans le dépôt.
4. Déployer, ouvrir l'URL fournie, vérifier la pastille
   « Sauvegarde serveur active » puis une fiche déjà traitée.

## Essai local

    docker build -t hympyr-cockpit .
    docker run --rm -p 8501:8501 -e HYMPYR_DATABASE_URL="<url pooler>" hympyr-cockpit

puis http://localhost:8501.

## Points de vigilance

- Le plan gratuit de certains hébergeurs met le service en veille : prévoir un
  plan payant si les commerciales l'utilisent toute la journée.
- Derrière un proxy ou un iframe (par exemple Hugging Face Spaces), Streamlit
  peut exiger `--server.enableCORS=false --server.enableXsrfProtection=false`.
- Les droits d'accès (qui peut ouvrir l'URL) et le registre des traitements
  doivent être traités avant la mise en service.
