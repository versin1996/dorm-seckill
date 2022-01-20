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

    let token = getCookie("token")
	$.ajax({
        type: "post",
        url: "http://www.liwang.zhangqx.com/result",
        data: {"token": token},
        success: (data, status) => {
            data = JSON.parse(data)
            console.log(data)
            if(data["buildingName"]) {
                $("#desc").html("")
                $("#live").css("display", "block")
            }
            else {
                $("#desc").html("同学你莫得宿舍，赶快去选！")
                $("#choose").css("display", "block")
            }
            $("#building").val(data["buildingName"])
            $("#unit").val(data["unitName"])
            $("#dorm").val(data["dormName"])
        }
    })
})