"""Diagnostic de déploiement — à utiliser UNIQUEMENT pour isoler une panne.

Ne contient aucune donnée client et n'affiche jamais les secrets (seulement
leur présence). À déployer comme fichier principal à la place de app.py, puis
à supprimer une fois le problème compris.
"""

from __future__ import annotations

import importlib
import importlib.metadata as md
import os
import platform
import py_compile
import sys
import time
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Diagnostic Hympyr", page_icon="🩺")
st.title("🩺 Diagnostic de déploiement")
st.success("Le serveur Streamlit démarre : le dépôt, l'installation et la plateforme fonctionnent.")

st.subheader("1. Environnement")
st.write(f"Python **{platform.python_version()}** — {platform.platform()}")
st.write(f"Répertoire de travail : `{os.getcwd()}`")

st.subheader("2. Paquets installés")
for paquet in ("streamlit", "pandas", "openpyxl", "psycopg", "psycopg-binary", "psycopg-pool"):
    try:
        st.write(f"- `{paquet}` {md.version(paquet)}")
    except md.PackageNotFoundError:
        st.error(f"- `{paquet}` : ABSENT")

st.subheader("3. Secrets (présence uniquement)")
try:
    url = str(st.secrets["database"]["url"]).strip()
    st.write("- `database.url` : présent")
    st.write(f"- schéma : `{url.split('://', 1)[0]}`, hôte : `{url.rsplit('@', 1)[-1].split('/', 1)[0]}`")
except Exception as exc:  # noqa: BLE001 — diagnostic : on veut tout voir
    url = ""
    st.warning(f"- `database.url` : absent ou illisible ({type(exc).__name__})")
try:
    st.write(f"- `motsdepasse` : {sorted(st.secrets['motsdepasse'].keys())}")
except Exception:  # noqa: BLE001
    st.write("- `motsdepasse` : absent (les empreintes du code seront utilisées)")

st.subheader("4. Fichiers de l'application")
racine = Path(__file__).parent
for nom in ("app.py", "script.py"):
    chemin = racine / nom
    try:
        py_compile.compile(str(chemin), doraise=True)
        st.write(f"- `{nom}` : {chemin.stat().st_size // 1024} Ko, syntaxe OK")
    except Exception as exc:  # noqa: BLE001
        st.error(f"- `{nom}` : {type(exc).__name__} — {exc}")
try:
    importlib.import_module("script")
    st.write("- `import script` : OK")
except Exception as exc:  # noqa: BLE001
    st.error(f"- `import script` : {type(exc).__name__} — {exc}")

st.subheader("5. Connexion Supabase")
if not url:
    st.info("Aucune URL de base : test impossible.")
elif st.button("Tester la connexion (8 s max)"):
    debut = time.perf_counter()
    try:
        import psycopg

        with psycopg.connect(url, connect_timeout=8) as con:
            ligne = con.execute("SELECT current_database(), version()").fetchone()
        st.success(f"Connexion OK en {time.perf_counter() - debut:.1f} s — base `{ligne[0]}`")
        st.code(ligne[1])
    except Exception as exc:  # noqa: BLE001
        # Le message psycopg peut citer l'hôte mais pas le mot de passe.
        st.error(f"Échec après {time.perf_counter() - debut:.1f} s : {type(exc).__name__}")
        st.code(str(exc).replace(url, "<url masquée>"))

st.caption(f"Interpréteur : {sys.executable}")
