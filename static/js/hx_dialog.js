var myModal = new bootstrap.Modal(document.getElementById('modal'));

;(function () {
    htmx.on('htmx:afterSwap', function (evt) {
        // swap되는 target부모가 dialog인 경우
        if (evt.detail.target.id === 'dialog') {
            myModal.show();
        }
    })
})();
