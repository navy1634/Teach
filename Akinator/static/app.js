const url = "http://127.0.0.1:8000/set_data";

function click_select(select_id) {
  var json_def = { ans: select_id };
  post(url, json_def); // サーバーへ回答を送信
  q_text = get(); // サーバーから質問を受信
  set_question(q_text); // 質問の変更
  set_image(); // 画像の変更
}

function set_image() {
  var random = Math.floor(Math.random() * 3);
  document.getElementById(
	"image"
  ).src = `static/images/gennbaneko${random}.png`;
}

function get() {
  let request = new XMLHttpRequest();

  request.onreadystatechange = function () {
	if ((request.readyState == 4) & (request.status == 200)) {
	  let node = document.getElementById("question_text");
	  var obj = JSON.parse(request.responseText);
	  node.innerText = obj.question;
	  // console.log(obj.question)
	}
  };

  request.open("GET", "http://localhost:8000/get_data", true);
  request.send();
  return "OK";
}

function post(url, data) {
  let request = new XMLHttpRequest();
  request.open("POST", url, true);
  var post_json = JSON.stringify(data);

  request.setRequestHeader("Content-Type", "application/json");
  request.send(post_json);
}

q_number = 1;
function set_question(txt) {
  q_number += 1;
  let question_number = document.getElementById("question_number");
  question_number.innerText = `Q${q_number}`;
  document.getElementById("question_text").txt = txt;
}
