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

    // function createToast(message) {
    //     const element = htmx.find("[data-toast-template]").cloneNode(true);
    //
    //     // 카피본에서는 data-toast-template 속성 삭제
    //     delete element.dataset.toastTemplate;
    //
    //     // message.text / .css를 사용해서 템플릿 복사본에 입히기
    //     element.className += " " + message.css;
    //
    //     // 템플릿 복사본 내에서 .toast-body를 data-toast-body 속성으로 찾아 텍스트 넣어주기
    //     htmx.find(element, "[data-toast-body]").innerText = message.text;
    //
    //     // 컨테이너 찾아서 템플릿 복사본 넣어주기
    //     htmx.find("[data-toast-container]").appendChild(element);
    //
    //
    //     const toast = new bootstrap.Toast(element, toastOptions);
    //     //container에 넣은 뒤, boostrap Toast로 생성하여 show
    //     toast.show();
    // }
    //
    //
    // htmx.on('messages', function (evt) {
    //     evt.detail.value.forEach(createToast)
    //     // Show all existsing toasts, except the template
    // });
    //

    // template을 제외하고 안띄워진 것이 있다면, 시작시 띄우기 for template렌더링
    // context로 message를 넘겨준 경우? 렌더링 된 것 띄우기 -> onLoad에서 처리됨.
    // htmx.findAll(".toast:not([data-toast-template])").forEach((element) => {
    //     const toast = new bootstrap.Toast(element, toastOptions)
    //     toast.show()
    // });


    // for oob
    // onLoad는 init + swap + oob-swap 모두에서 인식되어 작동한다.
    htmx.onLoad(() => {
        // 1. oob-swap되어 렌더링된 .toast 엘리먼트들을 찾아서 순회
        htmx.findAll(".toast").forEach((element) => {
            // 2. new를 뺀 bootstrap.Toast의 .getInstance()를 사용하여, 해당 엘리먼트에 대한 boostrap toast 초기화가 되었는지 확인한다.
            //    1) 이미 초기화 & show가 꺼졌다면(hide) -> .dispose()로 bootstrap 폐기 + element.remove()로 제거한다.
            //    2) 초기화가 안되었다면 -> new bootstrap.Toast()로 초기화하고 show()한다.
            let toast = bootstrap.Toast.getInstance(element)
            const isHidden = !element.classList.contains("show");
            if (toast && isHidden) {
                // boostrap 폐기
                toast.dispose()
                // Remove hidden toasts
                element.remove()
            }

            // 3. 아직 초기화가 안되었다면, new bootstrap.Toast()로 초기화한 뒤, .show()를 통해 toast를 띄운다.
            if (!toast) {
                const toast = new bootstrap.Toast(element, toastOptions)
                toast.show();
            }
        })
    })
})();
