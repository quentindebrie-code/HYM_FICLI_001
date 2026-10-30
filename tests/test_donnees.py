"""Couche données : verrou optimiste, réattribution, restauration CSV."""
import io

from streamlit.testing.v1 import AppTest

from conftest import APP


def executer_dans_app(corps: str) -> dict:
    """Exécute `corps` avec les fonctions de app.py, sans l'interface (tout ce qui
    précède la création du coffre : configuration, base, accès aux données)."""
    source = APP.read_text(encoding="utf-8").split("coffre = coffre_fichier()")[0]
    at = AppTest.from_string(source + "\n" + corps, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at.session_state["res"]


def test_version_incrementee_et_refus_si_perimee(base):
    res = executer_dans_app('''
enregistrer("K1", "Chloé", statut="Fait ✅")
v1 = numero_version(lire_fiche("K1")["version"])
enregistrer("K1", "Patricia", version_attendue=v1, note="a")
v2 = numero_version(lire_fiche("K1")["version"])
try:
    enregistrer("K1", "Chloé", version_attendue=v1, note="périmée")
    refus = False
except ConflitEnregistrement as c:
    refus = c.actuel["note"]
try:                                    # fiche jamais enregistrée : on attend la version 0
    enregistrer("K2", "Chloé", version_attendue=3, note="x")
    refus_k2 = False
except ConflitEnregistrement:
    refus_k2 = True
st.session_state["res"] = dict(v1=v1, v2=v2, refus=refus, note=lire_fiche("K1")["note"], refus_k2=refus_k2,
                               k2_absente=lire_fiche("K2") == {})
''')
    assert (res["v1"], res["v2"]) == (1, 2)
    assert res["refus"] == "a" and res["note"] == "a"
    assert res["refus_k2"] and res["k2_absente"]


def test_reattribution_admin_invalide_les_formulaires_ouverts(base):
    res = executer_dans_app('''
enregistrer("K1", "Chloé", statut="Fait ✅")
v = numero_version(lire_fiche("K1")["version"])
reattribuer("K1", "", "À appeler", "Quentin", {"traite_par": "Chloé", "statut": "Fait ✅"})
try:
    enregistrer("K1", "Chloé", version_attendue=v, statut="Fait ✅")
    refus = False
except ConflitEnregistrement:
    refus = True
st.session_state["res"] = dict(refus=refus, version=numero_version(lire_fiche("K1")["version"]),
                               statut=lire_fiche("K1")["statut"])
''')
    assert res == {"refus": True, "version": 2, "statut": "À appeler"}


def test_restauration_csv_nécrase_pas_une_base_deja_alimentee(base):
    res = executer_dans_app('''
import io
enregistrer("K1", "Chloé", statut="Fait ✅", note="saisie récente")
csv = "code_client;statut;note;traite_par\\nK1;À appeler;ancienne sauvegarde;Chloé\\nK2;Fait ✅;fiche absente;Patricia\\n".encode()
n, ignorees = importer_suivi_clients_csv(io.BytesIO(csv), creer_seulement=True)
st.session_state["res"] = dict(n=n, ignorees=ignorees, k1=lire_fiche("K1")["note"],
                               k1_statut=lire_fiche("K1")["statut"], k2=lire_fiche("K2")["note"])
''')
    assert res == {"n": 1, "ignorees": 1, "k1": "saisie récente", "k1_statut": "Fait ✅", "k2": "fiche absente"}


def test_restauration_csv_sur_base_vide_reste_integrale(base):
    res = executer_dans_app('''
import io
csv = "code_client;statut;note;traite_par\\nK1;Fait ✅;ancienne;Chloé\\n".encode()
n, ignorees = importer_suivi_clients_csv(io.BytesIO(csv))
st.session_state["res"] = dict(n=n, ignorees=ignorees, k1=lire_fiche("K1")["note"])
''')
    assert res == {"n": 1, "ignorees": 0, "k1": "ancienne"}
