"""Outillage des tests : l'application complète tourne sous streamlit.testing,
sur une base SQLite jetable, avec plusieurs sessions simultanées.

Deux sessions AppTest partagent le même processus et donc les mêmes caches
(`st.cache_data`, `st.cache_resource`), exactement comme deux commerciales
connectées à la même instance Streamlit.
"""
import datetime as dt
import io
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app.py"
NB_CLIENTS = 12
# Tri alphabétique sur « Client N » : C000, C001, C010, C011, C002, …
ORDRE_FILE = ["C000", "C001", "C010", "C011", "C002", "C003", "C004", "C005", "C006", "C007", "C008", "C009"]


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setenv("HYMPYR_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("HYMPYR_DATABASE_URL", raising=False)
    st.cache_data.clear()
    st.cache_resource.clear()

    clients = pd.DataFrame({
        "Code client": [f"C{i:03d}" for i in range(NB_CLIENTS)],
        "Raison sociale / Nom": [f"Client {i}" for i in range(NB_CLIENTS)],
        "Type client": ["Professionnel"] * NB_CLIENTS,
        "Ville": ["Lyon"] * NB_CLIENTS,
    })
    adresses = pd.DataFrame({
        "Code adresse": [f"A{i:03d}" for i in range(6)],
        "Code client mère": ["C000"] * 6,
        "Nom site": [f"Site {i}" for i in range(6)],
    })
    tampon = io.BytesIO()
    with pd.ExcelWriter(tampon, engine="openpyxl") as xw:
        clients.to_excel(xw, sheet_name="Clients", index=False)
        adresses.to_excel(xw, sheet_name="Adresses livraison", index=False)

    # Premier passage : l'application crée le schéma, puis on y dépose le classeur maître.
    AppTest.from_file(str(APP), default_timeout=60).run()
    con = sqlite3.connect(tmp_path / "suivi_appels.db")
    con.execute("INSERT OR REPLACE INTO fichiers (cle, nom, contenu, maj_le) "
                "VALUES ('fichier_maitre', 't.xlsx', ?, '2026-01-01T00:00:00')", (tampon.getvalue(),))
    con.commit()
    con.close()
    st.cache_resource.clear()
    return tmp_path


class Poste:
    """Une commerciale devant son navigateur."""

    def __init__(self, nom: str, role: str = "commercial"):
        self.nom = nom
        self.at = AppTest.from_file(str(APP), default_timeout=60)
        self.at.session_state["utilisateur"] = nom
        self.at.session_state["role"] = role
        self.at.session_state["demo_active"] = False
        self.at.run()
        assert not self.at.exception, [e.value for e in self.at.exception]

    # — lecture de l'écran —
    def fiche_affichee(self) -> str:
        return [t.key for t in self.at.text_area if t.key.startswith("note_C")][0].replace("note_", "")

    def bouton(self, fragment: str):
        return [b for b in self.at.button if fragment in b.label][0]

    def a_bouton(self, fragment: str) -> bool:
        return any(fragment in b.label for b in self.at.button)

    # — actions —
    def suivant(self, fois: int = 1):
        for _ in range(fois):
            self.bouton("Suivant").click().run()

    def precedent(self, fois: int = 1):
        for _ in range(fois):
            self.bouton("Précédent").click().run()

    def acces_direct(self, code: str):
        champ = [t for t in self.at.sidebar.text_input if t.label == "Code client exact"][0]
        champ.input(code).run()

    def enregistrer(self):
        self.bouton("Enregistrer").click().run()

    def actualiser(self):
        self.bouton("Actualiser").click().run()


def lignes(dossier: Path, table: str = "suivi") -> list[tuple]:
    con = sqlite3.connect(dossier / "suivi_appels.db")
    try:
        return con.execute(f"SELECT * FROM {table}").fetchall()
    finally:
        con.close()


def poser_verrou(dossier: Path, code: str, utilisateur: str, type_fiche: str = "client") -> None:
    """Simule « utilisateur a ouvert la fiche » (ce que fait marquer_presence)."""
    con = sqlite3.connect(dossier / "suivi_appels.db")
    con.execute("INSERT OR REPLACE INTO verrous VALUES (?,?,?,?,?)",
                (f"{type_fiche}:{code}:{utilisateur}", type_fiche, code, utilisateur,
                 dt.datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()
