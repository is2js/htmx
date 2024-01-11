const myToast = new bootstrap.Toast(document.getElementById('toast'));
const toastBody = document.getElementById('toast-body');
;(function(){

    htmx.on('showMessage', function (evt) {
        toastBody.innerHTML = evt.detail.value;
        myToast.show();
    });

})();