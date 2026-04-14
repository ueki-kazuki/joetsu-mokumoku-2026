import streamlit as st  # ウェブアプリを作るためのライブラリ
import requests          # インターネット上のAPIにアクセスするためのライブラリ
import boto3             # AWSのサービスを使うためのライブラリ
import json              # データをJSON形式に変換するためのライブラリ

# ブラウザのタブに表示されるタイトルとアイコンを設定する
st.set_page_config(page_title="NASA Dashboard", page_icon="🚀")
# アプリの見出しを表示する
st.title("🌌 NASA 宇宙探検ダッシュボード")

# 画面左側のサイドバーにAPIキーと日付の入力欄を作る
with st.sidebar:
    st.header("設定")
    # NASAのAPIキーを入力するテキストボックス（デフォルトはDEMO_KEY）
    nasa_key = st.text_input("NASA API Keyを入力", value="DEMO_KEY", type="password")
    # 見たい画像の日付を選ぶカレンダーUI
    target_date = st.date_input("見たい日付を選択してください")

# 使い方の説明を青いボックスで表示する
st.info("日付を選んで『宇宙を探索する』ボタンを押してみよう！")


def fetch_nasa_apod(api_key, date):
    """NASAのAPIにリクエストを送り、指定した日付の宇宙画像情報を取得する"""
    # APIのURL（api_keyとdateをパラメータとして渡す）
    url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}&date={date}"
    # URLにHTTPリクエストを送る
    response = requests.get(url)
    # エラー（404や429など）があれば例外を発生させる
    response.raise_for_status()
    # レスポンスをJSON形式（辞書型）に変換して返す
    return response.json()


def ask_bedrock(text):
    """AWSのBedrockを通じてAIに英語の解説を日本語に要約させる"""
    # BedrockのAPIクライアントを作成する
    bedrock = boto3.client(service_name='bedrock-runtime', region_name='ap-northeast-1')
    # AIへの指示文（プロンプト）を作る
    prompt = f"以下の宇宙に関する解説を、中高生がワクワクするような親しみやすい日本語で150文字程度で要約して解説してください。原文: {text}"
    # AIに送るデータをJSON形式に変換する
    body = json.dumps({"messages": [{"role": "user", "content": [{"text": prompt}]}]})
    # AIモデル（Amazon Nova Lite）を呼び出す
    response = bedrock.invoke_model(body=body, modelId="amazon.nova-lite-v1:0")
    # レスポンスのJSONを解析して、AIが生成したテキストを取り出す
    response_body = json.loads(response.get('body').read())
    return response_body['output']['message']['content'][0]['text']


# 「宇宙を探索する」ボタンが押されたときの処理
if st.button("宇宙を探索する"):
    # ぐるぐるのローディング表示をしながら処理を実行する
    with st.spinner("NASAのデータベースにアクセス中..."):
        try:
            # NASA APIから画像情報を取得する
            data = fetch_nasa_apod(nasa_key, target_date)
        except requests.exceptions.HTTPError as e:
            # HTTPエラー（APIキーが間違っている、未来の日付など）のとき
            st.error(f"APIエラー: {e.response.status_code} - {e.response.text}")
            st.stop()
        except requests.exceptions.RequestException as e:
            # ネットワークエラーなど通信に問題があるとき
            st.error(f"通信エラー: {e}")
            st.stop()

        if "url" in data:
            # 画像のタイトルを表示する
            st.subheader(data.get("title", "無題の天体"))

            # 画像か動画かによって表示方法を切り替える
            if data.get("media_type") == "image":
                st.image(data["url"], width="stretch")
            else:
                st.video(data["url"])

            # 英語の解説文をセッションに保存しておく（後でAIに渡すため）
            st.session_state['explanation'] = data.get("explanation", "")
            st.write("---")
            st.caption("NASAによる原文解説 (English):")
            st.write(st.session_state['explanation'])

# 解説文が保存されているときだけAI解説ボタンを表示する
if 'explanation' in st.session_state:
    # 「AIに日本語で解説してもらう」ボタンが押されたときの処理
    if st.button("AIに日本語で解説してもらう"):
        with st.spinner("AIが宇宙の謎を解読中..."):
            # BedrockのAIに英語の解説を日本語に要約させる
            result = ask_bedrock(st.session_state['explanation'])
            st.success("🛰️ AIによる解説")
            st.write(result)
