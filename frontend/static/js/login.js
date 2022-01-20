$(document).ready(() => {
	$("#login").click(() => {
        let username = $("#username").val()
        let password = $("#password").val()
        $.ajax({
            type: "post",
            url: "http://www.liwang.zhangqx.com/login",
            data: {"username": username, "password": password},
            success: function (data, status) {
                console.log(data)
                window.location.href="http://www.liwang.zhangqx.com/"
            }
        })
    })

})