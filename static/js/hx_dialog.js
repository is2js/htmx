const myModal = new bootstrap.Modal(document.getElementById('modal'));

;(function () {
    // 서버렌더링 html을 직접적으로 swap못하여 hx-target="#id명시"가 불가능한 경우 ex CUD로 204 NoContent => modal요소 .hide();
    // 즉, 신호만 받고 다른 것을 변경해야하는 경우 -> hx-target="this"만 걸어두고 여기서 target.id를 확인하여 -> 이벤트를 처리한다.
    htmx.on('htmx:afterSwap', function (evt) {
        // hx-target="this"(만) 명시된 요소들 + swap후 HX-Trigger에 의한 swap직전의 요소들도 순차적으로 다 잡히게 됨.
        // -> evt.detail.target.id를 확인하여  어떤 hx-target="this"인지 명시하여 처리한다.
        if (evt.detail.target.id === 'dialog') {
            console.log('show modal');
            myModal.show();
        }
    })

    // 서버렌더링 html을 직접적으로 swap못하여 hx-target="#id명시"가 불가능한 경우 ex CUD로 204 NoContent => modal요소 .hide();
    // 즉, 신호만 받고 다른 것을 변경해야하는 경우 -> hx-target="this"만 걸어두고 여기서 target.id를 확인하여 -> 이벤트를 처리한다.
    htmx.on("htmx:beforeSwap", function (evt) {
        // hx-target="this"(만) 명시된 요소들 + swap후 HX-Trigger에 의한 swap직전의 요소들도 순차적으로 다 잡히게 됨.
        // -> evt.detail.target.id를 확인하여  어떤 hx-target="this"인지 명시하여 처리한다.

        const noResponse = !evt.detail.xhr.response;
        if ((evt.detail.target.id === "dialog") && noResponse) {
            //console.log('hide modal')
            myModal.hide();
            // 204응답이 아닌 경우 -> 200응답에 & response가 비어있는 경우 -> swap자체가 안일어나도록 ex> 204 NoContent or [200 + empty response] 등..
            // add뿐만 아니라 edit에서 200응답이 왔어도 swap은 안일어나도록
            evt.detail.shouldSwap = false
        }

        // modal이 닫힌 뒤, 안에 내용 지우기
        htmx.on("hidden.bs.modal", () => {
            //console.log('hidden.bs.modal')
            document.getElementById("dialog").innerHTML = ""
        })
    })
})();
