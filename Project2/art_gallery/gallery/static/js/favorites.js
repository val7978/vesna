document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.card-heart').forEach(heart => {
        heart.addEventListener('click', function() {
            const artworkId = this.dataset.id;
            toggleFavorite(artworkId, this);
        });
    });
});

function toggleFavorite(artworkId, element) {
    fetch(`/toggle-favorite/${artworkId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if(data.status === 'added') {
            element.innerHTML = '♥';
            element.classList.add('liked');
        } else {
            element.innerHTML = '♡';
            element.classList.remove('liked');
        }
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}