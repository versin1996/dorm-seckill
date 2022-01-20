function show(label) {
	if($(label).next().css("display") == "none") {
		$(label).nextUntil("div").css("display", "block")
	}
	else {
		$(label).nextUntil("div").css("display", "none")
	}
}

$(document).ready(function() {
	$.ajax({
        type: "get",
        url: "http://www.liwang.zhangqx.com/info",
        success: function (data, status) {
			data = JSON.parse(data)
			$("#name").val(data["name"])
			$("#sex").val(data["sex"])
			$("#stuno").val(data["username"])
			$("#authentication").val(data["authentication"])
			buildings = data["buildings"]
			for(let building in buildings) {
				$(".dorm-info").append('<div class="weui-cell weui-cell_access" onclick="show(this)">' + building + '</div>')
				for(let dorm in buildings[building]) {
					if(dorm != '0')
						$(".dorm-info").append('<p class="weui-cell weui-cell_access dn">>&nbsp&nbsp 剩余 ' + dorm + ' 个床位的宿舍数量：' + buildings[building][dorm] + '</p>')
				}
			}
        }
    })
})
