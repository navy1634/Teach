# -*- coding utf-8, LF -*-

# 必要なモジュールのインポート
import json
import os
import random
from datetime import timedelta

import pandas as pd
from flask import Flask, render_template, request, session
from flask_cors import CORS

# Webサーバの初期設定
app = Flask(__name__)
cors = CORS(app, supports_credentials=True)
app.secret_key = "users"  # session の暗号、復号に用いる
app.permanent_session_lifetime = timedelta(minutes=10)  # session の保存時間

# データの初期設定
DATA_DIR = os.getcwd() + "/data"
# 質問情報
with open(DATA_DIR + "/questions.json", "r", encoding="utf-8") as f:
    questions_data_org = json.load(f)

# アンケート結果
survey_org = pd.read_csv(DATA_DIR + "/Answers.csv", encoding="utf-8")

# 全データの保存先
users_dict: dict = {}


@app.route("/")
def root() -> str:
    # HTMLの表示
    # 表紙の表示
    return render_template("index.html", static_url_path="/static/images")


@app.route("/result")
def result() -> str:
    user_id = session["user_id"]
    df_survey = users_dict[user_id]["survey"]

    if session["status"] == 1:  # 対象が特定できた場合
        print(df_survey["name"].to_list())
        name = df_survey["name"].to_list()[0]
        result_sentence = f"あなたは ”{name}” さんですか？"
    elif session["status"] == 2:  # 特定できなかった場合
        result_sentence = "あなたが誰かわかりませんでした……"
    else:
        raise ValueError

    # HTMLの表示
    return render_template("result.html", static_url_path="/static/images", result_sentence=result_sentence)


@app.route("/akinator")
def main() -> str:
    session.permanent = True

    # USER_ID の発行
    if "user_id" not in session:
        user_id = f"{random.randint(0, 100000000-1) :08d}"  # 乱数で生成
        session["user_id"] = user_id

    # 初期設定
    # USER_ID を基に管理する
    user_id = session["user_id"]
    users_dict[user_id] = dict()  # 個人データ保存の辞書
    users_dict[user_id]["survey"] = survey_org.copy()  # アンケートデータ
    users_dict[user_id]["question"] = questions_data_org.copy()  # 質問データ

    # 一つ目の質問
    questions = users_dict[user_id]["question"]  # 全質問の情報
    content = "sex"  # とりあえず性別から
    statement = questions[content]["statement"]  # 質問文
    choices = questions[content]["choices"]  # 選択肢
    choice_target = random.choice(choices)

    # 情報の保存
    session["content"] = content
    session["choice_target"] = choice_target

    if "{0}" in statement:
        statement = statement.format(choice_target)

    # HTMLの表示
    return render_template("akinator.html", static_url_path="/static/images")


@app.route("/request", methods=["POST"])
def post_item():
    user_id = session["user_id"]
    questions = users_dict[user_id]["question"]
    # print(request.method, session)

    df_survey = users_dict[user_id]["survey"]
    print("========================================")
    print("残質問数 : ", len(questions.keys()))
    print("残質問欄 : ", questions.keys())
    print("候補 : ", len(df_survey))

    # 条件の取得
    content = session["content"]
    choice_target = session["choice_target"]
    ans = request.json["Q"]["ans"]
    print("質問対象 : ", content)
    print("回答対象 : ", choice_target, type(choice_target))
    print("YES(0)/NO(1) : ", ans)
    print("session : ", session)

    # 判断
    if ans == 0:
        df_survey = df_survey[df_survey[content] == choice_target]
    elif ans == 1:
        df_survey = df_survey[df_survey[content] != choice_target]
    elif ans == 2:
        pass
    else:
        print("その他")

    # 聞いた質問を省く
    del questions[content]

    # 結果の保存
    users_dict[user_id]["survey"] = df_survey
    users_dict[user_id]["question"] = questions

    return {}


@app.route("/request", methods=["GET"])
def get_item() -> dict:
    user_id = session["user_id"]
    questions = users_dict[user_id]["question"]
    # print(request.method, session)

    # 条件判断
    df_survey = users_dict[user_id]["survey"]
    if len(df_survey) == 0:  # 条件に合う人が居なかった場合
        session_status = 2
        session["status"] = session_status
        print("対象者が見つかりませんでした")
        return {"result_status": session_status}

    elif len(df_survey) == 1:  # 1人に特定できた場合
        session_status = 1
        session["status"] = session_status
        target_name = df_survey["name"].to_list()[0]
        print(target_name)
        return {"result_status": session_status}

    else:
        session_status = 0
        session["status"] = session_status

    # 質問文の選択
    content = random.choice(list(questions.keys()))
    print("GET KEYS : ", questions.keys(), content)  # 確認
    # 質問対象の一覧
    choices = questions[content]["choices"]
    # 質問対象の選択
    choice_target = random.choice(choices)

    # 質問情報の保存
    session["content"] = content
    session["choice_target"] = choice_target
    print("Change Content", content)

    # 質問文の作成
    statement = questions[content]["statement"]  # 質問文の取得
    if "{0}" in statement:
        statement = statement.format(choice_target)

    return {"result_status": session_status, "question": statement}


@app.route("/reset", methods=["GET"])
def reset() -> dict:
    # 初期化
    user_id = session["user_id"]
    users_dict[user_id]["survey"] = survey_org.copy()
    users_dict[user_id]["question"] = questions_data_org.copy()
    return {"result_status": 0, "question": ""}


if __name__ == "__main__":
    # サーバの実行
    app.run(host="127.0.0.1", port=8000, debug=True)
