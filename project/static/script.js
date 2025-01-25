document.addEventListener('DOMContentLoaded', function () {
    const searchForm = document.getElementById('search-form');
    const seriesContainer = document.querySelector('#all-series .series-container');
    const recommendationsSection = document.getElementById('recommendations');

    // Gérer la recherche
    searchForm.addEventListener('submit', function (event) {
        event.preventDefault();
        const formData = new FormData(searchForm);
        const query = formData.get('query');

        fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                // Cacher les recommandations
                if (recommendationsSection) {
                    recommendationsSection.style.display = 'none';
                }

                // Effacer les anciennes séries et afficher les résultats
                seriesContainer.innerHTML = '';
                data.results.forEach(serie => {
                    const serieCard = document.createElement('div');
                    serieCard.classList.add('series-card');
                    serieCard.innerHTML = `
                        <img src="${serie.image}" alt="Image de ${serie.title}" class="series-image">
                        <div class="series-info">
                            <h2>${serie.title}</h2>
                            <p>${serie.description}</p>
                            <button class="like-btn" data-title="${serie.title}">J'aime</button>
                        </div>
                    `;
                    seriesContainer.appendChild(serieCard);
                });

                // Réattacher les événements "J'aime"
                addLikeButtonListeners();
            }
        })
        .catch(error => console.error('Erreur:', error));
    });

    // Fonction pour les boutons "J'aime"
    function addLikeButtonListeners() {
        const likeButtons = document.querySelectorAll('.like-btn');
        likeButtons.forEach(button => {
            button.addEventListener('click', function () {
                const title = this.getAttribute('data-title');

                fetch('/like', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ title: title })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        this.style.backgroundColor = 'green';
                        this.innerText = 'Ajouté aux favoris';
                    }
                })
                .catch(error => console.error('Erreur:', error));
            });
        });
    }

    // Initialiser les boutons "J'aime"
    addLikeButtonListeners();
});
