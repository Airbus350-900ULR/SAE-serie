from whoosh.index import open_dir

def get_series_from_index(index_dir):
    """
    Récupère les titres des séries depuis l'index Whoosh.
    """
    try:
        ix = open_dir(index_dir)
    except Exception as e:
        print(f"Erreur lors de l'ouverture de l'index : {e}")
        return []

    titles = []
    with ix.searcher() as searcher:
        for fields in searcher.all_stored_fields():
            titles.append(fields['title'])
    return titles
import os
import sqlite3
import requests

# Configuration TMDb
TMDB_API_KEY = "ff4251479664a8576a45d0809b94dd5f"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
IMAGE_FOLDER = "./static/images"
DATABASE = "series.db"

# Créer le dossier pour les images si inexistant
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Initialiser la base de données
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                image_path TEXT,
                tmdb_id INTEGER UNIQUE NOT NULL
            )
        ''')
        conn.commit()

from urllib.parse import urlencode
import wordninja

def normalize_title(title):
    """
    Divise un titre collé en mots avec des espaces.
    """
    split_title = wordninja.split(title)
    return " ".join(split_title).capitalize()

def get_tmdb_info(title):
    """
    Recherche les informations de la série sur TMDb.
    Effectue la recherche avec un titre normalisé (espaces) mais conserve le titre original.
    """
    # Normaliser le titre pour l'API TMDb
    normalized_title = normalize_title(title)
    search_url = f"{TMDB_BASE_URL}/search/tv"
    params = {
        "api_key": TMDB_API_KEY,
        "query": normalized_title,
        "language": "fr-FR"
    }

    response = requests.get(search_url, params=params)
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            first_result = results[0]
            # Utiliser le titre original (sans espace) pour enregistrer l'image
            return {
                "title": first_result.get("name"),
                "description": first_result.get("overview"),
                "image": f"https://image.tmdb.org/t/p/w500{first_result.get('poster_path')}" if first_result.get("poster_path") else None,
                "original_title": title
            }
    # Si aucune donnée trouvée, retourne un titre par défaut
    return {
        "title": normalize_title(title),
        "description": "Aucune description disponible.",
        "image": None,
        "original_title": title
    }



# Téléchargement d'une image et stockage local
def download_image(image_path, series_title):
    if not image_path:
        return None
    img_url = f"https://image.tmdb.org/t/p/w500{image_path}"
    local_filename = f"{IMAGE_FOLDER}/{series_title.replace(' ', '_').replace('/', '_')}.jpg"
    response = requests.get(img_url, stream=True)
    if response.status_code == 200:
        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return local_filename
    return None

# Insérer les données dans la base SQLite
def save_to_db(title, description, image_path, tmdb_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO series (title, description, image_path, tmdb_id)
                VALUES (?, ?, ?, ?)
            ''', (title, description, image_path, tmdb_id))
            conn.commit()
        except sqlite3.IntegrityError:
            print(f"'{title}' est déjà enregistré.")
def fetch_and_store_series_from_index(index_dir):
    # Récupérer les titres des séries depuis l'index Whoosh
    titles = get_series_from_index(index_dir)
    print(f"{len(titles)} séries trouvées dans l'index.")

    # Récupérer les données depuis TMDb et les stocker localement
    for title in titles:
        print(f"Traitement de la série : {title}")
        tmdb_data = get_tmdb_info(title)
        if tmdb_data:
            description = tmdb_data.get("overview", "Aucune description disponible.")
            image_path = tmdb_data.get("poster_path")
            local_image_path = download_image(image_path, title)
            tmdb_id = tmdb_data.get("id")
            save_to_db(title, description, local_image_path, tmdb_id)
        else:
            print(f"Aucune donnée trouvée pour : {title}")

def fetch_and_store_series(series_list):
    """
    Récupère et stocke les séries sans vérification de doublons.
    """
    for title in series_list:
        normalized_title = normalize_title(title)  # Titre avec espaces
        print(f"Traitement de la série : {normalized_title} (original : {title})")
        
        # Récupération des données TMDb
        tmdb_data = get_tmdb_info(title)
        if tmdb_data:
            description = tmdb_data.get("description", "Aucune description disponible.")
            image_url = tmdb_data.get("image")
            original_title = tmdb_data.get("original_title", title)

            # Télécharger l'image en utilisant le titre original (sans espaces)
            local_image_path = download_image(image_url, original_title)

            # Sauvegarder dans la base de données
            save_to_db(normalized_title, description, local_image_path, tmdb_data.get("title"))
        else:
            print(f"Aucune donnée trouvée pour : {normalized_title}")

def clear_database():
    """
    Supprime toutes les données existantes dans la base de données.
    """
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM series")  # Supprime toutes les lignes
        conn.commit()
    print("Base de données réinitialisée.")
 
if __name__ == "__main__":
    # Chemin vers l'index Whoosh
    INDEX_DIR = r"C:\Users\Etudiant\Documents\GitHub\SAE-serie\project\index"

    # Initialiser la base de données et réinitialiser son contenu
    init_db()
    clear_database()

    # Récupérer toutes les séries depuis l'index
    all_series = get_series_from_index(INDEX_DIR)

    # Récupérer et stocker les séries
    fetch_and_store_series(all_series)

    print("Toutes les séries ont été traitées et enregistrées.")
