from flask import Flask, render_template, request, jsonify
from whoosh.index import open_dir
from whoosh.qparser import MultifieldParser
from whoosh import scoring
import os

# Initialisation de Flask
app = Flask(__name__)

# Chemin vers l'index Whoosh
index_dir = r"C:\Users\Etudiant\Documents\GitHub\SAE-serie\project\index"

def search_series(query, limit=5):
    """
    Recherche les séries les plus pertinentes dans l'index Whoosh.
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
            recommendations.append({
                "title": result["title"],  # Titre de la série
                "score": result.score      # Pertinence
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
