import streamlit as st  # ウェブアプリを作るためのライブラリ
import requests          # インターネット上のAPIにアクセスするためのライブラリ
import boto3             # AWSのサービスを使うためのライブラリ
import json              # データをJSON形式に変換するためのライブラリ

# ブラウザのタブに表示されるタイトルとアイコンを設定する
st.set_page_config(page_title="NASA Mars Rover Dashboard", page_icon="🔴")
# アプリの見出しを表示する
st.title("🔴 NASA 火星探査ローバー写真ビューア")

# 画面左側のサイドバーにAPIキーとローバー設定の入力欄を作る
with st.sidebar:
    st.header("設定")
    # NASAのAPIキーを入力するテキストボックス（デフォルトはDEMO_KEY）
    nasa_key = st.text_input("NASA API Keyを入力", value="DEMO_KEY", type="password")
    # 探索するローバーを選ぶセレクトボックス
    rover = st.selectbox("ローバーを選択", ["curiosity", "opportunity", "spirit"],
                         format_func=lambda x: {"curiosity": "キュリオシティ（2012年〜）", "opportunity": "オポチュニティ（2004〜2018年）", "spirit": "スピリット（2004〜2010年）"}[x])
    # 火星の日数（Sol）を入力する数値入力ボックス（Sol=火星での1日）
    sol = st.number_input("Sol（火星の日数）を入力", min_value=0, max_value=5000, value=100, step=10)
    # 利用可能なカメラの説明を表示する
    st.caption("💡 Sol=0が着陸日。キュリオシティは3000 Sol以上のデータがあります。")

# 使い方の説明を青いボックスで表示する
st.info("ローバーとSol（火星での日数）を選んで『火星を探索する』ボタンを押してみよう！")


def fetch_mars_photos(api_key, rover, sol):
    """NASAのMars Rover Photos APIにリクエストを送り、指定ローバーの写真を取得する"""
    # APIのURL（rover名・sol・api_keyをパラメータとして渡す）
    url = f"https://mars-photos.herokuapp.com/api/v1/rovers/{rover}/photos?sol={sol}&api_key={api_key}&page=1"
    # URLにHTTPリクエストを送る
    response = requests.get(url)
    # エラー（404や429など）があれば例外を発生させる
    response.raise_for_status()
    # レスポンスの中にある「photos」リストを返す
    return response.json().get("photos", [])


def ask_bedrock(summary):
    """AWSのBedrockを通じてAIに火星探査データを日本語でわかりやすく解説させる"""
    # BedrockのAPIクライアントを作成する
    bedrock = boto3.client(service_name='bedrock-runtime', region_name='ap-northeast-1')
    # AIへの指示文（プロンプト）を作る
    prompt = (
        f"以下はNASAの火星探査ローバーが撮影した写真のデータです。"
        f"中高生が火星探査にワクワクするような親しみやすい日本語で、"
        f"探査の様子を200文字程度で解説してください。\n\n{summary}"
    )
    # AIに送るデータをJSON形式に変換する
    body = json.dumps({"messages": [{"role": "user", "content": [{"text": prompt}]}]})
    # AIモデル（Amazon Nova Lite）を呼び出す
    response = bedrock.invoke_model(body=body, modelId="amazon.nova-lite-v1:0")
    # レスポンスのJSONを解析して、AIが生成したテキストを取り出す
    response_body = json.loads(response.get('body').read())
    return response_body['output']['message']['content'][0]['text']


# 「火星を探索する」ボタンが押されたときの処理
if st.button("火星を探索する"):
    # ぐるぐるのローディング表示をしながら処理を実行する
    with st.spinner("NASAのデータベースにアクセス中..."):
        try:
            # Mars Rover Photos APIから写真データを取得する
            photos = fetch_mars_photos(nasa_key, rover, sol)
        except requests.exceptions.HTTPError as e:
            # HTTPエラー（APIキーが間違っているなど）のとき
            st.error(f"APIエラー: {e.response.status_code} - {e.response.text}")
            st.stop()
        except requests.exceptions.RequestException as e:
            # ネットワークエラーなど通信に問題があるとき
            st.error(f"通信エラー: {e}")
            st.stop()

    if not photos:
        # この日の写真がなかったときのメッセージ
        st.warning(f"Sol {sol} の写真は見つかりませんでした。別のSolを試してみてください。")
    else:
        # 表示する写真を最大9枚に絞る
        display_photos = photos[:9]
        st.metric("取得した写真数", f"{len(photos)} 枚（最大9枚を表示）")

        # 使われたカメラの種類を集める
        cameras = list({p["camera"]["full_name"] for p in display_photos})
        st.write(f"**使用カメラ:** {', '.join(cameras)}")

        # AIに渡すためのサマリーテキストを作る
        summary_lines = [
            f"ローバー: {rover.capitalize()}, Sol: {sol}, 撮影枚数: {len(photos)}",
            f"使用カメラ: {', '.join(cameras)}",
        ]

        # 3列のグリッドレイアウトで写真を表示する
        cols = st.columns(3)
        for i, photo in enumerate(display_photos):
            # 写真のURL・カメラ名・撮影日を取り出す
            img_url = photo["img_src"]
            camera_name = photo["camera"]["full_name"]
            earth_date = photo["earth_date"]

            # 表示する列を順番に切り替える（0→1→2→0→1...）
            col = cols[i % 3]
            with col:
                # 火星の写真を表示する
                st.image(img_url, caption=f"{camera_name}\n地球日: {earth_date}", use_container_width=True)

        # AIに渡すサマリーをセッションに保存しておく
        st.session_state['mars_summary'] = "\n".join(summary_lines)

# サマリーが保存されているときだけAI解説ボタンを表示する
if 'mars_summary' in st.session_state:
    if st.button("AIに火星の様子を解説してもらう"):
        with st.spinner("AIが火星探査データを解読中..."):
            # BedrockのAIに火星探査データを解説させる
            result = ask_bedrock(st.session_state['mars_summary'])
            st.success("🚀 AIによる解説")
            st.write(result)
