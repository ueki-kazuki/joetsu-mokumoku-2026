import streamlit as st  # ウェブアプリを作るためのライブラリ
import requests          # インターネット上のAPIにアクセスするためのライブラリ
import boto3             # AWSのサービスを使うためのライブラリ
import json              # データをJSON形式に変換するためのライブラリ
from datetime import date as date_type  # 今日の日付を取得するためのライブラリ

# ブラウザのタブに表示されるタイトルとアイコンを設定する
st.set_page_config(page_title="NASA EPIC Dashboard", page_icon="🌏")
# アプリの見出しを表示する
st.title("🌏 NASA 地球まるごとビューア（EPIC）")

# 画面左側のサイドバーにAPIキーと設定の入力欄を作る
with st.sidebar:
    st.header("設定")
    # NASAのAPIキーを入力するテキストボックス（デフォルトはDEMO_KEY）
    nasa_key = st.text_input("NASA API Keyを入力", value="DEMO_KEY", type="password")
    # 画像の種類を選ぶラジオボタン（natural=自然色、enhanced=強調色）
    color = st.radio("画像タイプ", ["natural", "enhanced"], format_func=lambda x: {"natural": "自然色", "enhanced": "強調色（植生など）"}[x])
    # 見たい日付を選ぶカレンダーUI（デフォルトは今日から数日前）
    target_date = st.date_input("日付を選択", value=date_type(2026, 4, 13))

# 使い方の説明を青いボックスで表示する
st.info("日付と画像タイプを選んで『地球を眺める』ボタンを押してみよう！")


def fetch_epic_images(api_key, color, target_date):
    """NASAのEPIC APIにリクエストを送り、指定日付の地球全体画像の一覧を取得する"""
    # 日付をYYYY-MM-DD形式の文字列に変換する
    date_str = str(target_date)
    # APIのURL（color と date をパスパラメータとして渡す）
    url = f"https://api.nasa.gov/EPIC/api/{color}/date/{date_str}?api_key={api_key}"
    # URLにHTTPリクエストを送る
    response = requests.get(url)
    # エラー（404や429など）があれば例外を発生させる
    response.raise_for_status()
    # レスポンスをJSON形式（リスト型）に変換して返す
    return response.json()


def build_image_url(api_key, color, image_name, date_str):
    """画像名と日付から実際の画像URLを組み立てる"""
    # 日付文字列（例: "2026-04-13 00:50:27"）から年・月・日を取り出す
    year = date_str[:4]
    month = date_str[5:7]
    day = date_str[8:10]
    # EPICの画像はアーカイブURLからPNG形式で取得できる
    return f"https://api.nasa.gov/EPIC/archive/{color}/{year}/{month}/{day}/png/{image_name}.png?api_key={api_key}"


def ask_bedrock(summary):
    """AWSのBedrockを通じてAIに地球の画像情報を日本語でわかりやすく解説させる"""
    # BedrockのAPIクライアントを作成する
    bedrock = boto3.client(service_name='bedrock-runtime', region_name='ap-northeast-1')
    # AIへの指示文（プロンプト）を作る
    prompt = (
        f"以下はNASAのEPICカメラが宇宙から撮影した地球の画像データです。"
        f"中高生が地球の美しさや宇宙視点に興味を持てるような親しみやすい日本語で、"
        f"200文字程度で解説してください。\n\n{summary}"
    )
    # AIに送るデータをJSON形式に変換する
    body = json.dumps({"messages": [{"role": "user", "content": [{"text": prompt}]}]})
    # AIモデル（Amazon Nova Lite）を呼び出す
    response = bedrock.invoke_model(body=body, modelId="amazon.nova-lite-v1:0")
    # レスポンスのJSONを解析して、AIが生成したテキストを取り出す
    response_body = json.loads(response.get('body').read())
    return response_body['output']['message']['content'][0]['text']


# 「地球を眺める」ボタンが押されたときの処理
if st.button("地球を眺める"):
    # ぐるぐるのローディング表示をしながら処理を実行する
    with st.spinner("NASAのデータベースにアクセス中..."):
        try:
            # EPIC APIから画像一覧を取得する
            images = fetch_epic_images(nasa_key, color, target_date)
        except requests.exceptions.HTTPError as e:
            # HTTPエラー（APIキーが間違っている、データがない日付など）のとき
            st.error(f"APIエラー: {e.response.status_code} - {e.response.text}")
            st.stop()
        except requests.exceptions.RequestException as e:
            # ネットワークエラーなど通信に問題があるとき
            st.error(f"通信エラー: {e}")
            st.stop()

    if not images:
        # この日付の画像がなかったときのメッセージ
        st.warning("この日付の画像は見つかりませんでした。別の日付を試してみてください。")
    else:
        # 取得した画像の総数を表示する（最大5枚まで表示）
        display_images = images[:5]
        st.metric("この日の地球画像枚数", f"{len(images)} 枚（最大5枚を表示）")

        # AIに渡すためのサマリーテキストを作る
        summary_lines = []

        # 3列のグリッドレイアウトで画像を表示する
        cols = st.columns(3)
        for i, img_data in enumerate(display_images):
            image_name = img_data.get("image", "")
            date_str = img_data.get("date", "")
            # 中心座標（撮影時に地球の中心が写っていた位置）を取り出す
            centroid = img_data.get("centroid_coordinates", {})
            lat = centroid.get("lat", 0)
            lon = centroid.get("lon", 0)

            # 画像のURLを組み立てる
            img_url = build_image_url(nasa_key, color, image_name, date_str)
            # 表示する列を順番に切り替える（0→1→2→0→1...）
            col = cols[i % 3]
            with col:
                # 地球の画像を表示する
                st.image(img_url, caption=f"{date_str}\n緯度:{lat:.1f} 経度:{lon:.1f}", use_container_width=True)

            # AIに渡すサマリーに追加する
            summary_lines.append(f"撮影日時: {date_str}, 中心座標: 緯度{lat:.2f} 経度{lon:.2f}")

        # AIに渡すサマリーをセッションに保存しておく
        st.session_state['epic_summary'] = f"日付: {target_date}, 種類: {color}\n" + "\n".join(summary_lines)

# サマリーが保存されているときだけAI解説ボタンを表示する
if 'epic_summary' in st.session_state:
    if st.button("AIに地球の様子を解説してもらう"):
        with st.spinner("AIが地球の画像データを解読中..."):
            # BedrockのAIに地球の画像データを解説させる
            result = ask_bedrock(st.session_state['epic_summary'])
            st.success("🌍 AIによる解説")
            st.write(result)
