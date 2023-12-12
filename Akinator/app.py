# -*- coding utf-8, LF -*-

# 必要なモジュールのインポート
import json
import os
import random
import string
from datetime import timedelta

import pandas as pd
from flask import Flask, render_template, request, session
from flask_cors import CORS

# データの初期設定
DATA_DIR = os.getcwd() + "/data"

# 質問文と選択肢の情報
with open(DATA_DIR + "/questions.json", "r", encoding="utf-8") as f:
    question_data = json.load(f)

question_priority_dict = {
    "essential": ["student_num", "club", "birthday", "living"],
    "important": ["grade", "class", "subject", "bus", "season", "3tennkai", "learning"],
    "normal": ["sex", "door", "fishmeet", "blood", "kinotake", "ricebread", "income", "committee", "heyfever", "grasses", "science", "apple", "asmr", "food"],
}


# アンケート結果
survey_org = pd.read_csv(DATA_DIR + "/Answers.csv", encoding="utf-8")

# データの保存先
all_users_dict: dict[str, dict] = dict()

# Webサーバの初期設定
app = Flask(__name__)
cors = CORS(app, supports_credentials=True)
app.secret_key = "".join(random.choices(string.ascii_letters + string.digits, k=24))  # session の暗号、復号に用いる
app.permanent_session_lifetime = timedelta(minutes=10)  # session の保存時間

NORMAL = 0
CAN_FIND = 1
CANNOT_FIND = 2


@app.route("/")
def root() -> str:
    # HTMLの表示
    # 表紙の表示
    return render_template("index.html", static_url_path="/static/images")


@app.route("/akinator")
def main() -> str:
    session.permanent = True

    # USER_ID の発行
    if "user_id" not in session:
        user_id = f"{random.randint(0, 100000000-1) :08d}"  # 乱数で生成
        session["user_id"] = user_id

    # 初期設定
    # USER_ID を基に管理する
    user_dict = dict()  # 個人データ保存の辞書
    user_dict["survey"] = survey_org.copy()  # アンケートデータ
    user_dict["question_priority"] = question_priority_dict.copy()  # 質問の一覧
    user_dict["sentence"] = ""
    user_dict["question_list"] = list()
    session["count"] = 0

    user_id = session["user_id"]
    all_users_dict[user_id] = user_dict

    # 一つ目の質問
    question_priority = all_users_dict[user_id]["question_priority"]  # 全質問の情報
    content = random.choice(question_priority["normal"])  # 最初の質問を選ぶ
    statement = question_data[content]["statement"]  # 質問文
    choices = question_data[content]["choices"]  # 選択肢
    choice_target = random.choice(choices)
    print("質問対象 : ", content)
    print("回答対象 : ", choice_target)

    # 情報の保存
    session["content"] = content
    session["choice_target"] = choice_target

    if "{0}" in statement:
        statement = statement.format(choice_target)

    # HTMLの表示
    return render_template("akinator.html", static_url_path="/static/images", question_statement=statement)


@app.route("/request", methods=["POST"])
def post_item() -> dict:
    user_id = session["user_id"]
    print("========================================")
    # print(request.method, session)

    # 生徒の回答データ
    df_survey_def = all_users_dict[user_id]["survey"]
    print("候補数 : ", len(df_survey_def))

    if len(df_survey_def) < 2:  # 1人に特定できた場合
        return {}

    # 条件の取得
    content = session["content"]
    choice_target = session["choice_target"]
    ans = request.json["Q"]["ans"]
    print("質問対象 : ", content)
    print("回答対象 : ", choice_target)
    print("YES(0)/NO(1) : ", ans)

    # 判断
    if ans == 0:
        df_survey = df_survey_def[df_survey_def[content] == choice_target]
    elif ans == 1:
        df_survey = df_survey_def[df_survey_def[content] != choice_target]
    elif ans == 2:
        df_survey = df_survey_def.copy()
    else:
        raise ValueError()

    # 結果の保存
    if len(df_survey) == 0:
        all_users_dict[user_id]["survey"] = df_survey_def
    else:
        all_users_dict[user_id]["survey"] = df_survey

    all_users_dict[user_id]["question_list"].append([content, choice_target, ans])
    return {}


@app.route("/request", methods=["GET"])
def get_item():
    user_id = session["user_id"]
    print("-------------------------")
    # print(request.method, session)

    # 条件判断
    df_survey = all_users_dict[user_id]["survey"]
    print("残候補数 : ", len(df_survey))
    if len(df_survey) == 0:  # 条件に合う人が居なかった場合
        session_status = CANNOT_FIND
        session["status"] = session_status
        result_sentence = "あなたが誰かわかりませんでした……"
        all_users_dict[user_id]["sentence"] = result_sentence
        print(result_sentence)
        return {"result_status": session_status, "statement": ""}

    elif len(df_survey) == 1:  # 1人に特定できた場合
        session_status = CAN_FIND
        session["status"] = session_status
        target_name = df_survey["name"].to_list()[0]
        result_sentence = f"""あなたは ”{target_name}” さんですか？"""
        all_users_dict[user_id]["sentence"] = result_sentence
        print(result_sentence)
        return {"result_status": session_status, "statement": ""}

    session_status = NORMAL
    session["status"] = session_status

    # 質問文の選択
    question_priority = all_users_dict[user_id]["question_priority"]  # 全質問の情報

    # 質問の重要性を考える
    len_df = len(df_survey)

    if len_df > 90:
        importance = "normal"
    elif len_df > 6:
        importance = "important"
    else:
        importance = "essential"

    # 重要性別のリストが空なら多い normal から選ぶ
    if len(question_priority[importance]) == 0:
        importance = "normal"
    elif len(question_priority["normal"]) == 0:
        importance = "important"
    elif len(question_priority["important"]) == 0:
        importance = "essential"
    elif len(question_priority["essential"]) == 0 and len(question_priority["normal"]) == 0 and len(question_priority["important"]) == 0:
        return {"result_status": CANNOT_FIND, "statement": "ERROR"}

    while True:
        # 質問対象の選択
        content = random.choice(question_priority[importance])
        # 聞いた質問を省く
        question_priority[importance].remove(content)
        # 選択肢が1つの場合飛ばす
        if len(df_survey[content].unique()) >= 2:
            break

    # 質問対象の一覧
    choices = question_data[content]["choices"]
    print("残質問一覧 : \n", question_priority)
    print("次の質問   : ", content)  # 確認
    # 質問対象の選択
    choice_target = random.choice(choices)

    # 質問情報の保存
    session["importance"] = importance
    session["content"] = content
    session["choice_target"] = choice_target

    # 質問文の作成
    statement = question_data[content]["statement"]  # 質問文の取得
    if "{0}" in statement:
        statement = statement.format(choice_target)
    print("質問文 : ", statement)

    return {"result_status": session_status, "statement": statement, "len": len_df}


@app.route("/back", methods=["GET"])
def back() -> dict:
    # 初期化
    user_id = session["user_id"]
    user_dict = all_users_dict[user_id]
    print("========================================")

    # 質問文の選択
    if len(user_dict["question_list"]) <= 2:
        return {"result_status": NORMAL}

    session_status = 0
    session["status"] = session_status

    content, choice_target, ans = user_dict["question_list"][-2]
    statement = question_data[content]["statement"]  # 質問文
    print("質問対象 : ", content)
    print("回答対象 : ", choice_target)
    print("YES(0)/NO(1) : ", ans)

    df = survey_org.copy()
    user_dict["question_list"] = user_dict["question_list"][:-1]
    for _content, _choice_target, _ans in user_dict["question_list"]:
        if _ans == 0:
            df = df[df[_content] == _choice_target]
        else:
            df = df[df[_content] != _choice_target]

    # 情報の保存
    user_dict["survey"] = df
    session["content"] = content
    session["choice_target"] = choice_target
    all_users_dict[user_id] = user_dict

    if "{0}" in statement:
        statement = statement.format(choice_target)

    return {"result_status": NORMAL, "statement": statement}

@app.route("/reset", methods=["GET"])
def reset() -> dict:
    # 初期化
    user_id = session["user_id"]
    user_dict = all_users_dict[user_id]
    user_dict["survey"] = survey_org.copy()
    user_dict["question_priority"] = question_priority_dict.copy()
    user_dict["sentence"] = ""

    # 一つ目の質問
    question_priority = user_dict["question_priority"]  # 全質問の情報
    content = random.choice(question_priority["normal"])
    statement = question_data[content]["statement"]  # 質問文
    choices = question_data[content]["choices"]  # 選択肢
    choice_target = random.choice(choices)
    print("質問対象 : ", content)
    print("回答対象 : ", choice_target)

    # 情報の保存
    session["content"] = content
    session["choice_target"] = choice_target

    if "{0}" in statement:
        statement = statement.format(choice_target)

    return {"result_status": NORMAL, "statement": statement}

@app.route("/answer", methods=["GET"])
def answer():
    user_id = session["user_id"]
    result_sentence = all_users_dict[user_id]["sentence"]
    return render_template("answer.html", static_url_path="/static", result_sentence=result_sentence)

@app.route("/result", methods=["GET"])
def result():
    if session["status"] == 1:
        result_text = "よぉし！ 正解！！\n魔人は何でもお見通しだ !"
    else:
        user_id = session["user_id"]
        result_text = all_users_dict[user_id]["sentence"]

    return render_template("result.html", static_url_path="/static", result_text=result_text)


if __name__ == "__main__":
    # サーバの実行
    app.run(host="127.0.0.1", port=8000, debug=True)
