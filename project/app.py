from flask import Flask, render_template, request, jsonify
from whoosh.index import open_dir
from whoosh.qparser import MultifieldParser
from whoosh import scoring
import sqlite3
import os
import wordninja

# Initialisation de Flask
app = Flask(__name__)

# Chemin vers l'index Whoosh
index_dir = r"C:\Users\etudiant\Documents\GitHub\SAE-serie\project\index"


# Chemin vers la base de données SQLite
DATABASE = "./series.db"

def normalize_title(title):
    """
    Divise un titre collé en mots avec des espaces.
    """
    split_title = wordninja.split(title)
    return " ".join(split_title).capitalize()

def get_local_info(title):
    """
    Récupère les informations locales pour une série depuis la base de données SQLite.
    """
    normalized_title = normalize_title(title)

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT description, image_path FROM series WHERE title = ?", (normalized_title,))
        row = cursor.fetchone()

    if row:
        description, image_path = row
        # Vérifier si l'image existe
        if image_path and os.path.exists(image_path):
            image_url = f"/static/images/{os.path.basename(image_path)}"
        else:
            image_url = None
        return {
            "title": normalized_title,
            "description": description if description else "Description non disponible.",
            "image": image_url
        }
    else:
        return {
            "title": normalized_title,
            "description": "Description non disponible.",
            "image": None
        }
def normalize_query(query):
    """
    Normalise une requête en retirant les espaces pour correspondre aux titres collés dans l'index.
    """
    return query.replace(" ", "").lower()

def search_series(query, limit=5):
    """
    Recherche les séries les plus pertinentes dans l'index Whoosh et complète avec les informations locales.
    Ajoute une priorité aux séries dont le titre contient directement le texte de recherche.
    """
    try:
        ix = open_dir(index_dir)
    except Exception as e:
        return {"error": f"Erreur lors de l'ouverture de l'index : {e}"}

    # Normaliser la requête pour correspondre aux titres collés
    normalized_query = normalize_query(query)

    with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
        parser = MultifieldParser(["title", "content"], schema=ix.schema)
        parsed_query = parser.parse(normalized_query)

        # Recherche dans l'index
        results = searcher.search(parsed_query, limit=None)  # Pas de limite initiale pour prioriser correctement

        recommendations = []
        for result in results:
            local_info = get_local_info(result["title"])

            # Calcul de la priorité en fonction de la correspondance
            title_lower = local_info["title"].lower()
            query_lower = normalized_query

            # Ajouter une priorité si le titre contient exactement ou partiellement la recherche
            priority = 0
            if query_lower == title_lower:
                priority = 100  # Correspondance exacte
            elif query_lower in title_lower:
                priority = 50   # Correspondance partielle

            recommendations.append({
                "title": local_info["title"],
                "description": local_info["description"],
                "image": local_info["image"],
                "score": result.score + priority  # Ajuster le score avec la priorité
            })

        # Trier les résultats par score décroissant
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        # Retourner les résultats avec une limite
        return {"results": recommendations[:limit]}


# Route pour la page d'accueil
@app.route("/")
def index():
    return render_template("index.html")

# Route pour effectuer une recherche
@app.route("/search", methods=["POST"])
def search():
    query = request.form.get("query")
    if not query:
        return jsonify({"error": "Veuillez entrer un texte pour effectuer la recherche."})

    # Effectuer la recherche
    search_results = search_series(query)

    return jsonify(search_results)

# Lancer le serveur Flask
if __name__ == "__main__":
    app.run(debug=True)
