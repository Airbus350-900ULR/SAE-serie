from flask import Flask, render_template, request, jsonify
from whoosh.index import open_dir
from whoosh.qparser import MultifieldParser
from whoosh import scoring
import os
import requests

# Initialisation de Flask
app = Flask(__name__)

# Chemin vers l'index Whoosh
index_dir = r"./index"

# Clé API et URL de base pour TMDb
TMDB_API_KEY = "ff4251479664a8576a45d0809b94dd5f"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

def get_tmdb_info(title):
    """
    Recherche les informations de la série sur TMDb.
    """
    search_url = f"{TMDB_BASE_URL}/search/tv"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "language": "fr-FR"
    }
    response = requests.get(search_url, params=params)
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            first_result = results[0]
            return {
                "title": first_result.get("name"),
                "description": first_result.get("overview"),
                "image": f"https://image.tmdb.org/t/p/w500{first_result.get('poster_path')}" if first_result.get("poster_path") else None
            }
    return {
        "title": title,
        "description": "Aucune description disponible.",
        "image": None
    }

def search_series(query, limit=5):
    """
    Recherche les séries les plus pertinentes dans l'index Whoosh et complète avec les informations TMDb.
    """
    try:
        ix = open_dir(index_dir)
    except Exception as e:
        return {"error": f"Erreur lors de l'ouverture de l'index : {e}"}

    with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
        parser = MultifieldParser(["title", "content"], schema=ix.schema)
        parsed_query = parser.parse(query)

        results = searcher.search(parsed_query, limit=limit)

        recommendations = []
        for result in results:
            tmdb_info = get_tmdb_info(result["title"])
            recommendations.append({
                "title": tmdb_info["title"],
                "description": tmdb_info["description"],
                "image": tmdb_info["image"],
                "score": result.score
            })
        return {"results": recommendations}

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
