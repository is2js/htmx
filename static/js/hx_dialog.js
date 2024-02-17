const modalElement = document.getElementById('modal');
let modal = new bootstrap.Modal(modalElement);

const mediaModalElement = document.getElementById('mediaModal');
let mediaModal = new bootstrap.Modal(mediaModalElement);

;(function () {
    // 서버렌더링 html을 직접적으로 swap못하여 hx-target="#id명시"가 불가능한 경우 ex CUD로 204 NoContent => modal요소 .hide();
    // 즉, 신호만 받고 다른 것을 변경해야하는 경우 -> hx-target="this"만 걸어두고 여기서 target.id를 확인하여 -> 이벤트를 처리한다.
    htmx.on('htmx:afterSwap', function (evt) {
        // hx-target="this"(만) 명시된 요소들 + swap후 HX-Trigger에 의한 swap직전의 요소들도 순차적으로 다 잡히게 됨.
        // -> evt.detail.target.id를 확인하여  어떤 hx-target="this"인지 명시하여 처리한다.
        if (evt.detail.target.id === 'dialog') {
            modal = bootstrap.Modal.getInstance(modalElement)
            if (modal) {
                // 1) 열림과 동시에 닫힘이 아니라면, dipose안되어있으니, 열기만
                modal.show();
            } else {
                // 2) 열림과 동시에 닫혀야해서, 먼저 일어나는 닫기에서 hide대신 dispose로 막나왔으면
                // -> 다음 열림을 위해 modal객체 생성만 해두기
                modal = new bootstrap.Modal(modalElement);
            }
        }

        if (evt.detail.target.id === 'mediaDialog') {
            mediaModal = bootstrap.Modal.getInstance(mediaModalElement)
            if (mediaModal) {
                mediaModal.show();
            } else {
                mediaModal = new bootstrap.Modal(mediaModalElement);
            }
        }

    })


    // 서버렌더링 html을 직접적으로 swap못하여 hx-target="#id명시"가 불가능한 경우 ex CUD로 204 NoContent => modal요소 .hide();
    // 즉, 신호만 받고 다른 것을 변경해야하는 경우 -> hx-target="this"만 걸어두고 여기서 target.id를 확인하여 -> 이벤트를 처리한다.
    // htmx.on("htmx:beforeSwap", function (evt) {
    //     // hx-target="this"(만) 명시된 요소들 + swap후 HX-Trigger에 의한 swap직전의 요소들도 순차적으로 다 잡히게 됨.
    //     // -> evt.detail.target.id를 확인하여  어떤 hx-target="this"인지 명시하여 처리한다.
    //
    //     const noResponse = !evt.detail.xhr.response;
    //     if ((evt.detail.target.id === "dialog") && noResponse) {
    //         console.log('hide modal')
    //         myModal.hide();
    //         // 204응답이 아닌 경우 -> 200응답에 & response가 비어있는 경우 -> swap자체가 안일어나도록 ex> 204 NoContent or [200 + empty response] 등..
    //         // add뿐만 아니라 edit에서 200응답이 왔어도 swap은 안일어나도록
    //         evt.detail.shouldSwap = false
    //     }
    //
    //     // modal이 닫힌 뒤, 안에 내용 지우기
    //     htmx.on("hidden.bs.modal", () => {
    //         //console.log('hidden.bs.modal')
    //         document.getElementById("dialog").innerHTML = ""
    //     })
    // })
    // // -> toast oob 렌더링 때문에, NoContent는 안온다.


    htmx.on("noContent", (evt) => {
        // 초기화 / show에서 이미 modal객체를 생성해놨는데, 혹시나 오류에 의해 객체가 없을 수 있으니
        // 없으면 생성해서 modal객체 무조건 획득은 상태
        modal = bootstrap.Modal.getOrCreateInstance(modalElement)

        // if (currentModal && modalElement.classList.contains("show")) {
        if (modalElement.classList.contains("show")) {
            // 1) 열림(느리지만 이전) -> 닫힘(빠름)이 구분동작여서 이미 열려있다면
            //  -> 닫기만
            modal.hide();
        } else {
            // 2) 열림->닫힘 동시동작인데, 느린 열람 때문에, 닫기에서 미리 못열리게 hide대신 dispose로 안열리게, modal객체 소멸시키기
            //    -> 열려고 할 때, modal객체가 dispose로 죽어있으면, 살리기만 하고 끝나서 안열린다.
            modal.dispose();
        }

        mediaModal = bootstrap.Modal.getOrCreateInstance(mediaModalElement)

        if (mediaModalElement.classList.contains("show")) {
            mediaModal.hide();
        } else {
            mediaModal.dispose();
        }

        evt.detail.shouldSwap = false // 200이라도 swap안일어나게 만들기
    })

    // modal이 닫히는 event(hidden.bs.modal by modal.hide(); ) -> dialog의 내용 지우기
    htmx.on("hidden.bs.modal", () => {
        console.log('hidden.bs.modal')
        document.getElementById("dialog").innerHTML = ""
        document.getElementById("mediaDialog").innerHTML = ""
    })

})();
