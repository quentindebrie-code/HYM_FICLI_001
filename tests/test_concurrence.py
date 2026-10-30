"""Régressions : deux commerciales en simultané sur le même outil.

Bug d'origine : des fiches « s'effaçaient » et il fallait ressaisir les informations.
Deux causes, reproduites ici :

1. la file d'appel était parcourue par numéro d'ordre ; quand l'autre commerciale
   ouvrait ou traitait une fiche située plus haut, le numéro désignait un autre
   client, le clic sur « Enregistrer » tombait dans le vide et la saisie était perdue ;
2. un formulaire resté ouvert avec d'anciennes valeurs pouvait, une fois enregistré,
   écraser le travail de l'autre (statut « Fait ✅ » retombant à « À appeler »).
"""
from conftest import ORDRE_FILE, Poste, lignes, poser_verrou

COL = {"code": 0, "statut": 1, "existe": 2, "produits": 3, "email": 4, "tel": 5, "note": 6, "traite_par": 10}


def fiche(dossier, code):
    return next((r for r in lignes(dossier) if r[0] == code), None)


# ── 1. La file bouge pendant la saisie ───────────────────────────────────────

def test_saisie_conservee_quand_une_fiche_plus_haut_quitte_la_file(base):
    patricia = Poste("Patricia")
    patricia.suivant(2)
    assert patricia.fiche_affichee() == ORDRE_FILE[2]            # C010
    patricia.at.text_area(key="note_C010").input("Rappel confirmé")

    # Chloé ouvre C000 : la fiche disparaît de la file de Patricia.
    poser_verrou(base, "C000", "Chloé")
    patricia.enregistrer()

    ligne = fiche(base, "C010")
    assert ligne is not None, "la saisie de Patricia a été perdue"
    assert ligne[COL["note"]] == "Rappel confirmé"
    assert ligne[COL["traite_par"]] == "Patricia"
    assert not patricia.at.exception


def test_pas_de_fiche_sautee_apres_enregistrement(base):
    chloe = Poste("Chloé")
    assert chloe.fiche_affichee() == "C000"
    chloe.at.selectbox(key="statut_C000").select("Fait ✅")
    chloe.enregistrer()
    # C000 quitte la file (« Non traité ») : on doit arriver sur C001, pas sur C010.
    assert chloe.fiche_affichee() == "C001"
    chloe.at.selectbox(key="statut_C001").select("Fait ✅")
    chloe.enregistrer()
    assert chloe.fiche_affichee() == "C010"
    assert {r[0] for r in lignes(base)} == {"C000", "C001"}


def test_fiche_ouverte_epinglee_si_lautre_la_traite(base):
    """Même filtres, la fiche disparaît parce que quelqu'un d'autre l'a traitée :
    elle reste à l'écran, le formulaire ne change pas sous les doigts."""
    chloe = Poste("Chloé")
    assert chloe.fiche_affichee() == "C000"
    patricia = Poste("Patricia")                                   # C000 masquée pour elle
    patricia.acces_direct("C000")
    patricia.at.selectbox(key="statut_C000").select("Fait ✅")
    patricia.enregistrer()

    chloe.actualiser()
    assert chloe.fiche_affichee() == "C000"                        # toujours sous ses yeux
    assert any("modifié" in w.value for w in chloe.at.warning)     # et elle est prévenue


def test_navigation_precedent_suivant_stable(base):
    chloe = Poste("Chloé")
    chloe.suivant(3)
    assert chloe.fiche_affichee() == ORDRE_FILE[3]
    chloe.precedent(2)
    assert chloe.fiche_affichee() == ORDRE_FILE[1]
    chloe.precedent(5)                                             # borne basse
    assert chloe.fiche_affichee() == ORDRE_FILE[0]


# ── 2. Formulaire périmé ─────────────────────────────────────────────────────

def _deux_postes_sur_c000():
    chloe = Poste("Chloé")
    chloe.acces_direct("C000")
    patricia = Poste("Patricia")
    patricia.acces_direct("C000")
    return chloe, patricia


def test_formulaire_perime_nécrase_pas_le_travail_de_lautre(base):
    chloe, patricia = _deux_postes_sur_c000()
    chloe.at.selectbox(key="statut_C000").select("Fait ✅")
    chloe.at.text_area(key="note_C000").input("Contrat gaz OK")
    chloe.at.text_input(key="email_C000").input("durand@client.fr")
    chloe.enregistrer()
    avant = fiche(base, "C000")
    assert avant[COL["statut"]] == "Fait ✅"

    patricia.actualiser()
    patricia.enregistrer()                                         # formulaire resté sur l'ancien état

    assert fiche(base, "C000") == avant, "le travail de Chloé a été écrasé"
    assert any("refusé" in e.value for e in patricia.at.error)
    assert patricia.a_bouton("Recharger")


def test_recharger_la_fiche_affiche_letat_en_base(base):
    chloe, patricia = _deux_postes_sur_c000()
    chloe.at.selectbox(key="statut_C000").select("À rappeler")
    chloe.at.text_area(key="note_C000").input("Rappeler jeudi")
    chloe.at.date_input(key="rappel_C000").set_value(__import__("datetime").date.today())
    chloe.enregistrer()

    patricia.actualiser()
    assert patricia.a_bouton("Recharger la fiche")                 # prévenue avant même d'enregistrer
    patricia.bouton("Recharger la fiche").click().run()

    assert patricia.at.selectbox(key="statut_C000").value == "À rappeler"
    assert patricia.at.text_area(key="note_C000").value == "Rappeler jeudi"
    assert not patricia.a_bouton("Recharger la fiche")

    # Après rechargement, son enregistrement est accepté.
    patricia.at.text_area(key="note_C000").input("Rappeler jeudi 10h")
    patricia.enregistrer()
    assert fiche(base, "C000")[COL["note"]] == "Rappeler jeudi 10h"


def test_enregistrements_successifs_dans_la_meme_session_sans_faux_conflit(base):
    chloe = Poste("Chloé")
    chloe.acces_direct("C000")
    for note in ("v1", "v2", "v3"):
        chloe.at.text_area(key="note_C000").input(note)
        chloe.enregistrer()
        assert not any("refusé" in e.value for e in chloe.at.error), note
        assert fiche(base, "C000")[COL["note"]] == note


def test_aller_retour_sur_une_fiche_ne_garde_pas_une_version_perimee(base):
    chloe = Poste("Chloé")
    chloe.suivant()                                                # C001
    chloe.precedent()                                              # C000
    # pendant ce temps, Patricia traite C000
    patricia = Poste("Patricia")
    patricia.acces_direct("C000")
    patricia.at.text_area(key="note_C000").input("Patricia")
    patricia.enregistrer()
    chloe.suivant()
    chloe.precedent()                                              # C000 est épinglée/réaffichée
    chloe.actualiser()
    if chloe.fiche_affichee() == "C000":
        assert not chloe.a_bouton("Recharger la fiche")            # version relue à la réouverture
        chloe.at.text_area(key="note_C000").input("Chloé complète")
        chloe.enregistrer()
        assert not any("refusé" in e.value for e in chloe.at.error)


# ── 3. Points de livraison ───────────────────────────────────────────────────

def _onglet_points(poste):
    poste.at.segmented_control(key="navigation_principale").set_value("📦  Points de livraison").run()


def test_points_livraison_saisie_conservee_et_pas_de_saut(base):
    patricia = Poste("Patricia")
    _onglet_points(patricia)
    cle = [t.key for t in patricia.at.text_input if t.key and t.key.startswith("referent_A")][0]
    code = cle.replace("referent_", "")
    patricia.at.text_input(key=cle).input("M. Martin")
    patricia.bouton("Enregistrer").click().run()
    lignes_adr = lignes(base, "suivi_adresses")
    assert [(r[0], r[1]) for r in lignes_adr] == [(code, "M. Martin")]
    suivante = [t.key for t in patricia.at.text_input if t.key and t.key.startswith("referent_A")][0]
    assert suivante.replace("referent_", "") == "A001"             # aucune adresse sautée


def test_points_livraison_formulaire_perime_refuse(base):
    chloe, patricia = Poste("Chloé"), Poste("Patricia")
    for p in (chloe, patricia):
        _onglet_points(p)
        champ = [t for t in p.at.text_input if t.label == "🔎 Code adresse exact (ex. 12771L56)"][0]
        champ.input("A000").run()
    chloe.at.text_input(key="referent_A000").input("M. Martin")
    chloe.bouton("Enregistrer").click().run()
    avant = lignes(base, "suivi_adresses")

    patricia.bouton("Actualiser").click().run()
    patricia.bouton("Enregistrer").click().run()
    assert lignes(base, "suivi_adresses") == avant
    assert any("refusé" in e.value for e in patricia.at.error)
