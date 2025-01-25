from flask import Flask, render_template, request, jsonify, url_for, redirect
import sqlite3
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pickle

# Initialisation de Flask
app = Flask(__name__)

# Chemin vers le répertoire de base de l'application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Chemin vers la base de données SQLite
DATABASE = os.path.join(BASE_DIR, "series.db")

# Dossier des images
IMAGES_DIR = os.path.join(BASE_DIR, "static", "images")
PLACEHOLDER_IMAGE = "placeholder.jpg"  # Nom du fichier de l'image par défaut

# Chemin pour charger les données TF-IDF pré-calculées
TFIDF_MODEL_FILE = os.path.join(BASE_DIR, "data", "tfidf_model.pkl")
SERIES_NAMES_FILE = os.path.join(BASE_DIR, "data", "series_names.pkl")

# Charger le modèle TF-IDF
with open(TFIDF_MODEL_FILE, "rb") as tfidf_file, open(SERIES_NAMES_FILE, "rb") as names_file:
    vectorizer, tfidf_matrix = pickle.load(tfidf_file)
    series_names = pickle.load(names_file)
print("Modèle TF-IDF chargé depuis le disque.")

# Initialisation de la base de données
with sqlite3.connect(DATABASE) as conn:
    cursor = conn.cursor()
    # Créer la table des séries likées si elle n'existe pas
    cursor.execute("CREATE TABLE IF NOT EXISTS liked_series (title TEXT UNIQUE)")
    conn.commit()

# Normaliser un titre (supprimer espaces, mettre en minuscule)
def normalize_title(title):
    return title.replace(" ", "").lower()

# Fonction de recherche par similarité
def search_series(query, limit=5):
    query_vector = vectorizer.transform([query])
    similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
    ranked_indices = np.argsort(similarities)[::-1][:limit]

    # Ajouter la priorité si le titre contient exactement le mot clé
    exact_matches = [
        (series, 1.0) for series in series_names
        if normalize_title(query) in normalize_title(series)
    ]
    ranked_results = [(series_names[idx], similarities[idx]) for idx in ranked_indices]

    # Mélanger les exact_matches en premier, suivis des résultats ordinaires
    combined_results = exact_matches + ranked_results
    seen_titles = set()
    unique_results = []
    for series, score in combined_results:
        if series not in seen_titles:
            unique_results.append((series, score))
            seen_titles.add(series)
    return unique_results[:limit]

# Récupérer les informations locales (description et image)
def get_local_info(title):
    normalized_title = normalize_title(title)
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, description FROM series WHERE REPLACE(LOWER(title), ' ', '') = ?", (normalized_title,))
        row = cursor.fetchone()

    if row:
        original_title, description = row
        image_file = f"{normalize_title(original_title)}.jpg"
        image_path_full = os.path.join(IMAGES_DIR, image_file)
        if os.path.exists(image_path_full):
            image_url = url_for('static', filename=f'images/{image_file}')
        else:
            image_url = url_for('static', filename=f'images/{PLACEHOLDER_IMAGE}')
        return {
            "title": original_title,  # Retourner le titre formaté depuis la base
            "description": description if description else "Description non disponible.",
            "image": image_url
        }
    else:
        return {
            "title": title,
            "description": "Description non disponible.",
            "image": url_for('static', filename=f'images/{PLACEHOLDER_IMAGE}')
        }

# Récupérer toutes les séries pour la page d'accueil
def get_all_series():
    series_list = []
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM series")
        rows = cursor.fetchall()
    for row in rows:
        title = row[0]
        local_info = get_local_info(title)
        series_list.append({
            "title": local_info["title"],
            "description": local_info["description"],
            "image": local_info["image"]
        })
    return series_list

# Récupérer les séries likées
def get_liked_series():
    liked_series = []
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM liked_series")
        rows = cursor.fetchall()
    for row in rows:
        title = row[0]
        local_info = get_local_info(title)
        liked_series.append({
            "title": local_info["title"],
            "description": local_info["description"],
            "image": local_info["image"]
        })
    return liked_series

app.route("/")
def index():
    all_series = get_all_series()
    recommendations = get_recommendations_based_on_likes()

    # Log pour diagnostiquer le problème
    print("Recommandations envoyées :", recommendations)

    return render_template("index.html", series=all_series, recommendations=recommendations)


# Obtenir des recommandations basées sur les séries likées
def get_recommendations_based_on_likes(limit=5):
    # Récupérer les titres des séries likées et les normaliser pour comparaison
    liked_titles = [normalize_title(title["title"]) for title in get_liked_series()]
    print("Titres likés normalisés :", liked_titles)

    if not liked_titles:
        return []

    # Calculer les similarités basées sur les séries likées
    liked_vectors = vectorizer.transform(liked_titles)
    similarities = cosine_similarity(liked_vectors, tfidf_matrix).mean(axis=0)
    ranked_indices = np.argsort(similarities)[::-1]

    recommendations = []
    for idx in ranked_indices:
        series = series_names[idx]  # Utiliser le titre d'origine
        normalized_series = normalize_title(series)  # Normaliser uniquement pour comparaison
        if normalized_series not in liked_titles:  # Exclure les séries déjà likées
            # Récupérer les informations de la base
            local_info = get_local_info(series)
            recommendations.append({
                "title": local_info["title"],  # Utiliser le titre d'origine de la base
                "description": local_info["description"],
                "image": local_info["image"]
            })
            if len(recommendations) == limit:
                break

    print("Recommandations finales :", [rec["title"] for rec in recommendations])
    return recommendations





# Ajouter une série aux favoris
def add_to_likes(title):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO liked_series (title) VALUES (?)", (title,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

# Route pour la page d'accueil
@app.route("/")
def index():
    all_series = get_all_series()
    recommendations = get_recommendations_based_on_likes()
    return render_template("index.html", series=all_series, recommendations=recommendations)

# Route pour afficher les séries likées
@app.route("/liked")
def liked():
    liked_series = get_liked_series()
    return render_template("liked.html", series=liked_series)

# Route pour effectuer une recherche
@app.route("/search", methods=["POST"])
def search():
    query = request.get_json().get("query")
    if not query:
        return jsonify({"error": "Veuillez entrer une requête."})

    search_results = search_series(query)
    results = []
    for series, similarity in search_results:
        local_info = get_local_info(series)
        results.append({
            "title": local_info["title"],
            "description": local_info["description"],
            "image": local_info["image"],
            "similarity": round(similarity, 4)
        })

    return jsonify({"results": results})




@app.route("/like", methods=["POST"])
def like():
    data = request.get_json()  # Récupère le corps JSON de la requête
    if not data or "title" not in data:
        return jsonify({"error": "Titre manquant."})

    title = data["title"]
    success = add_to_likes(title)
    return jsonify({"success": success})


# Route pour afficher uniquement les séries likées
@app.route("/mes-series")
def mes_series():
    liked_series = get_liked_series()
    return render_template("mes_series.html", series=liked_series)

@app.route("/unlike", methods=["POST"])
def unlike():
    data = request.get_json()
    if not data or "title" not in data:
        return jsonify({"error": "Titre manquant."})

    title = data["title"]
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM liked_series WHERE title = ?", (title,))
        conn.commit()

    return jsonify({"success": True})

# Lancer le serveur Flask
if __name__ == "__main__":
    app.run(debug=True)
