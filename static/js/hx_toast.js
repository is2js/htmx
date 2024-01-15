// const myToast = new bootstrap.Toast(document.getElementById('toast'),
//     {delay: 2000}
// );
// const toastBody = document.getElementById('toast-body');
//
// ;(function () {
//
//     htmx.on('showMessage', function (evt) {
//         toastBody.innerHTML = evt.detail.value;
//         myToast.show();
//     });
//
// })();



;(function () {
    const toastOptions = {delay: 2000};

    function createToast(message) {
        const element = htmx.find("[data-toast-template]").cloneNode(true);

        // 카피본에서는 data-toast-template 속성 삭제
        delete element.dataset.toastTemplate;

        // message.text / .css를 사용해서 템플릿 복사본에 입히기
        element.className += " " + message.css;

        // 템플릿 복사본 내에서 .toast-body를 data-toast-body 속성으로 찾아 텍스트 넣어주기
        htmx.find(element, "[data-toast-body]").innerText = message.text;

        // 컨테이너 찾아서 템플릿 복사본 넣어주기
        htmx.find("[data-toast-container]").appendChild(element);


        const toast = new bootstrap.Toast(element, toastOptions);
        //container에 넣은 뒤, boostrap Toast로 생성하여 show
        toast.show();
    }


    htmx.on('messages', function (evt) {
        evt.detail.value.forEach(createToast)
        // Show all existsing toasts, except the template
    });

    // template을 제외하고 안띄워진 것이 있다면, 시작시 띄우기
    htmx.findAll(".toast:not([data-toast-template])").forEach((element) => {
        const toast = new bootstrap.Toast(element, toastOptions)
        toast.show()
    });


})();
