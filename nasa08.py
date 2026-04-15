import streamlit as st  # ウェブアプリを作るためのライブラリ
import requests          # インターネット上のAPIにアクセスするためのライブラリ
import boto3             # AWSのサービスを使うためのライブラリ
import json              # データをJSON形式に変換するためのライブラリ
from datetime import date as date_type  # 日付を扱うためのライブラリ

# ブラウザのタブに表示されるタイトルとアイコンを設定する
st.set_page_config(page_title="NASA Earth Dashboard", page_icon="🛰️")
# アプリの見出しを表示する
st.title("🛰️ NASA 衛星画像ダッシュボード")

# プリセットの場所リスト（緯度・経度・場所名）
PRESET_LOCATIONS = {
    "東京": (35.6895, 139.6917),
    "ニューヨーク": (40.7128, -74.0060),
    "パリ": (48.8566, 2.3522),
    "シドニー": (-33.8688, 151.2093),
}

# 画面左側のサイドバーに設定の入力欄を作る
with st.sidebar:
    st.header("設定")
    # NASAのAPIキーを入力するテキストボックス（デフォルトはDEMO_KEY）
    nasa_key = st.text_input("NASA API Keyを入力", value="DEMO_KEY", type="password")

    st.subheader("プリセット場所")
    # プリセットの場所ボタンをサイドバーに表示する
    selected_preset = st.selectbox("場所を選ぶ", ["カスタム"] + list(PRESET_LOCATIONS.keys()))

    # プリセットが選ばれたとき、緯度・経度の初期値を変える
    if selected_preset != "カスタム":
        default_lat, default_lon = PRESET_LOCATIONS[selected_preset]
    else:
        # カスタムのデフォルトは東京
        default_lat, default_lon = 35.6895, 139.6917

    # 緯度を入力する数値入力ボックス
    lat = st.number_input("緯度（北がプラス）", min_value=-90.0, max_value=90.0, value=default_lat, step=0.01, format="%.4f")
    # 経度を入力する数値入力ボックス
    lon = st.number_input("経度（東がプラス）", min_value=-180.0, max_value=180.0, value=default_lon, step=0.01, format="%.4f")
    # 見たい日付を選ぶカレンダーUI
    target_date = st.date_input("日付を選択", value=date_type(2024, 1, 1))
    # 画像の範囲を調整するスライダー（dimが大きいほど広い範囲が写る）
    dim = st.slider("画像の範囲（度）", min_value=0.01, max_value=0.1, value=0.025, step=0.005, format="%.3f")

# 使い方の説明を青いボックスで表示する
st.info("場所と日付を選んで『衛星画像を取得する』ボタンを押してみよう！")


def fetch_earth_image(api_key, lat, lon, date, dim):
    """NASAのEarth APIにリクエストを送り、指定した場所・日付のランドサット衛星画像を取得する"""
    # APIのURL（緯度・経度・日付・範囲をパラメータとして渡す）
    url = (
        f"https://api.nasa.gov/planetary/earth/assets"
        f"?lon={lon}&lat={lat}&date={date}&dim={dim}&api_key={api_key}"
    )
    # URLにHTTPリクエストを送る
    response = requests.get(url)
    # エラー（404や429など）があれば例外を発生させる
    response.raise_for_status()
    # レスポンスをJSON形式（辞書型）に変換して返す
    return response.json()


def ask_bedrock(summary):
    """AWSのBedrockを通じてAIに衛星画像の場所情報を日本語でわかりやすく解説させる"""
    # BedrockのAPIクライアントを作成する
    bedrock = boto3.client(service_name='bedrock-runtime', region_name='ap-northeast-1')
    # AIへの指示文（プロンプト）を作る
    prompt = (
        f"以下はNASAのランドサット衛星が撮影した場所のデータです。"
        f"中高生がその場所や宇宙からの視点に興味を持てるような親しみやすい日本語で、"
        f"その場所の特徴や見どころを200文字程度で解説してください。\n\n{summary}"
    )
    # AIに送るデータをJSON形式に変換する
    body = json.dumps({"messages": [{"role": "user", "content": [{"text": prompt}]}]})
    # AIモデル（Amazon Nova Lite）を呼び出す
    response = bedrock.invoke_model(body=body, modelId="amazon.nova-lite-v1:0")
    # レスポンスのJSONを解析して、AIが生成したテキストを取り出す
    response_body = json.loads(response.get('body').read())
    return response_body['output']['message']['content'][0]['text']


# 「衛星画像を取得する」ボタンが押されたときの処理
if st.button("衛星画像を取得する"):
    # ぐるぐるのローディング表示をしながら処理を実行する
    with st.spinner("NASAのデータベースにアクセス中..."):
        try:
            # Earth APIから衛星画像データを取得する
            data = fetch_earth_image(nasa_key, lat, lon, target_date, dim)
        except requests.exceptions.HTTPError as e:
            # HTTPエラー（この日付・場所の画像がない場合など）のとき
            if e.response.status_code == 404:
                st.error("この日付・場所の衛星画像は見つかりませんでした。別の日付を試してみてください。")
            else:
                st.error(f"APIエラー: {e.response.status_code} - {e.response.text}")
            st.stop()
        except requests.exceptions.RequestException as e:
            # ネットワークエラーなど通信に問題があるとき
            st.error(f"通信エラー: {e}")
            st.stop()

    # 画像URLと撮影日を取り出す
    img_url = data.get("url")
    img_date = data.get("date", "不明")[:10]  # YYYY-MM-DD形式に切り取る

    if img_url:
        # 衛星画像を大きく表示する
        st.image(img_url, caption=f"📍 緯度:{lat:.4f} 経度:{lon:.4f} | 撮影日: {img_date}", use_container_width=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("緯度", f"{lat:.4f}°")
        with col2:
            st.metric("経度", f"{lon:.4f}°")
        with col3:
            st.metric("撮影日", img_date)

        # AI解説用のサマリーをセッションに保存しておく
        location_name = selected_preset if selected_preset != "カスタム" else f"緯度{lat:.4f} 経度{lon:.4f}"
        st.session_state['earth_summary'] = (
            f"場所: {location_name}, 緯度: {lat:.4f}, 経度: {lon:.4f}, "
            f"撮影日: {img_date}, 画像範囲: {dim}度"
        )
    else:
        st.warning("画像URLが取得できませんでした。")

# サマリーが保存されているときだけAI解説ボタンを表示する
if 'earth_summary' in st.session_state:
    if st.button("AIにこの場所を解説してもらう"):
        with st.spinner("AIが衛星画像データを解読中..."):
            # BedrockのAIに場所の情報を解説させる
            result = ask_bedrock(st.session_state['earth_summary'])
            st.success("🛰️ AIによる解説")
            st.write(result)
