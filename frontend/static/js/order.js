$(document).ready(() => {
    function getCookie(cname) {
        let name = cname + "="
        let ca = document.cookie.split(';')
        for(let i=0; i < ca.length; i++) {
            let c = ca[i].trim()
            if(c.indexOf(name)==0)
                return c.substring(name.length,c.length)
        }
        return ""
    }

	$("#cb").click(() => {
		if($("#cb").prop("checked")) {
			$(".authentication").css("display", "block")
        }
		else
			$(".authentication").css("display", "none")
	})

	$("#submit").click(() => {
        let token = getCookie("token")
		let building = $(".building").val()
		let bind = $(".bind").is(":checked")
        let auth = ""
		if(bind) {
            let auth1 = $("#auth1").val()
            let auth2 = $("#auth2").val()
            let auth3 = $("#auth3").val()
            if(auth1) {
                auth = auth1
            }
            if(auth2 && auth2 != auth1) {
                if(auth)
                    auth += "." + auth2
                else
                    auth = auth2
            }
            if(auth3 && auth3 != auth2 && auth3 != auth1) {
                if(auth) 
                    auth += "." + auth3
                else
                    auth = auth3
            }
        }
        if(!auth)
            bind = false
        $.ajax({
            type: "post",
            url: "http://www.liwang.zhangqx.com/order",
            data: {"token": token, "building": building, "bind": bind, "auth": auth},
            success: function (data, status) {
                if(data == "200") {
                    window.location.href="http://www.liwang.zhangqx.com/result"
                }
                else if(data == "404") {
                    $(".tips").html("没有满足条件的宿舍或同住人认证码错误！")
                    $(".tips").css("display", "block")
                } 
                else {
                    $(".tips").html("还未到选择宿舍时间，请耐心等待！")
                    $(".tips").css("display", "block")
                }

            }
        })
        $("#submit").disabled = true
    })

	$.ajax({
        type: "get",
        url: "http://www.liwang.zhangqx.com/building",
        success: (data, status) => {
			data = JSON.parse(data)
			for(let building in data.buildings) {
				$(".building").append("<option value=" + data.buildings[building] + ">" + data.buildings[building] + "</option>")
			}
        }
    })

    $.ajax({
        type: "get",
        url: "http://www.liwang.zhangqx.com/ordertime",
        success: (data, status) => {
            data = JSON.parse(data)
            console.log(data)
            $(".time").html("开始时间：" + data.orderTime)
        }
    })
})