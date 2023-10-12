# -*- coding utf-8, LF -*-

# 必要なモジュールのインポート
import json
import random
from datetime import timedelta

import pandas as pd
from flask import Flask, render_template, request, session
from flask_cors import CORS

# Webサーバの初期設定
app = Flask(__name__)
cors = CORS(app, supports_credentials=True)
app.secret_key = "users" # session の暗号、復号に用いる
app.permanent_session_lifetime = timedelta(minutes=10)  # session の保存時間

# データの初期設定
# 質問情報
with open("./data/questions.json", "r", encoding="utf-8") as f:
    questions_data_org = json.load(f)

# アンケート結果
survey_org = pd.read_csv("./data/Survey_Answers.csv", encoding="utf-8")

# 全データの保存先
users_dict: dict = {}


@app.route("/")
def root():
    session.permanent = True
    # USER_ID の発行
    if "user_id" not in session:
        user_id = f"{random.randint(0, 100000000-1) :08d}" # 乱数で生成
        session["user_id"] = user_id

    # 初期設定
    # USER_ID を基に管理する
    user_id = session["user_id"]
    users_dict[user_id] = dict()  # 個人データ保存の辞書
    users_dict[user_id]["survey"] = survey_org.copy() # アンケートデータ
    users_dict[user_id]["question"] = questions_data_org.copy() # 質問データ

    # 一つ目の質問
    questions = users_dict[user_id]["question"]  # 全質問の情報
    content = "sex"  # とりあえず性別から
    statement = questions[content]["statement"]  # 質問文
    choices = questions[content]["choices"]  # 選択肢
    choice_target = random.choice(list(choices.keys()))

    # 情報の保存
    session["content"] = content
    session["choice_target"] = choice_target

    if "{0}" in statement:
        statement = statement.format(choices[choice_target])

    # HTMLの表示
    return render_template("index.html", static_url_path="/static/images")


@app.route("/request", methods=["POST"])
def post_item():
    user_id = session["user_id"]
    questions = users_dict[user_id]["question"]
    # print(request.method, session)

    df_survey = users_dict[user_id]["survey"]
    print("========================================")
    print("残質問数 : ", len(questions.keys()))
    print("残質問数 : ", questions.keys())
    print("候補 : ", len(df_survey))

    # 条件の取得
    content = session["content"]
    choice_target = int(session["choice_target"])
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

    # 条件判断
    if len(df_survey) == 0:  # 条件に合う人が居なかった場合
        print("対象者が見つかりませんでした")
        return {"result_status": 2}

    elif len(df_survey) == 1:  # 1人に特定できた場合
        target_name = df_survey["name"].to_list()[0]
        print(target_name)
        return {"result_status": 1, "name": target_name}

    return {"result_status": 0}

@app.route("/request", methods=["GET"])
def get_item():
    user_id = session["user_id"]
    questions = users_dict[user_id]["question"]
    # print(request.method, session)

    content = random.choice(list(questions.keys()))
    print("GET KEYS : ", questions.keys(), content)
    choices = questions[content]["choices"]  # 質問対象
    choice_target = random.choice(list(choices.keys()))

    # 質問情報の保存
    session["content"] = content
    session["choice_target"] = int(choice_target)
    print("Change Content")

    # 質問文の作成
    statement = questions[content]["statement"]  # 質問文の取得
    if "{0}" in statement:
        parts = choices[choice_target]
        if parts == "その他":
            parts = "それ以外"

        statement = statement.format(choices[choice_target])

    return {"question": statement}


@app.route("/reset", methods=["GET"])
def reset():
    # 初期化
    user_id = session["user_id"]
    users_dict[user_id]["survey"] = survey_org.copy()
    users_dict[user_id]["question"] = questions_data_org.copy()
    return {"status": 0}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
