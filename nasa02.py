import streamlit as st  # ウェブアプリを作るためのライブラリ
import requests          # インターネット上のAPIにアクセスするためのライブラリ
import boto3             # AWSのサービスを使うためのライブラリ
import json              # データをJSON形式に変換するためのライブラリ
from datetime import timedelta  # 日付の計算に使うライブラリ

# ブラウザのタブに表示されるタイトルとアイコンを設定する
st.set_page_config(page_title="NASA NEO Dashboard", page_icon="☄️")
# アプリの見出しを表示する
st.title("☄️ NASA 小惑星接近ダッシュボード")

# 画面左側のサイドバーにAPIキーと日付の入力欄を作る
with st.sidebar:
    st.header("設定")
    # NASAのAPIキーを入力するテキストボックス（デフォルトはDEMO_KEY）
    nasa_key = st.text_input("NASA API Keyを入力", value="DEMO_KEY", type="password")
    # 検索開始日を選ぶカレンダーUI
    start_date = st.date_input("開始日")
    # 検索終了日（最大7日間まで）
    end_date = st.date_input("終了日", value=start_date + timedelta(days=1))

# 使い方の説明を青いボックスで表示する
st.info("日付範囲を選んで（最大7日間）『小惑星を探索する』ボタンを押してみよう！")


def fetch_neo_feed(api_key, start_date, end_date):
    """NASAのAPIにリクエストを送り、指定期間に地球に接近する小惑星の一覧を取得する"""
    url = (
        f"https://api.nasa.gov/neo/rest/v1/feed"
        f"?start_date={start_date}&end_date={end_date}&api_key={api_key}"
    )
    # URLにHTTPリクエストを送る
    response = requests.get(url)
    # エラー（404や429など）があれば例外を発生させる
    response.raise_for_status()
    # レスポンスをJSON形式（辞書型）に変換して返す
    return response.json()


def ask_bedrock(asteroids_summary):
    """AWSのBedrockを通じてAIに小惑星データを日本語でわかりやすく解説させる"""
    # BedrockのAPIクライアントを作成する
    bedrock = boto3.client(service_name='bedrock-runtime', region_name='ap-northeast-1')
    # AIへの指示文（プロンプト）を作る
    prompt = (
        f"以下は地球に接近する小惑星のデータです。"
        f"中高生がワクワクするような親しみやすい日本語で、"
        f"注目すべき小惑星を紹介しながら200文字程度で解説してください。\n\n{asteroids_summary}"
    )
    # AIに送るデータをJSON形式に変換する
    body = json.dumps({"messages": [{"role": "user", "content": [{"text": prompt}]}]})
    # AIモデル（Amazon Nova Lite）を呼び出す
    response = bedrock.invoke_model(body=body, modelId="amazon.nova-lite-v1:0")
    # レスポンスのJSONを解析して、AIが生成したテキストを取り出す
    response_body = json.loads(response.get('body').read())
    return response_body['output']['message']['content'][0]['text']


# 「小惑星を探索する」ボタンが押されたときの処理
if st.button("小惑星を探索する"):
    # 日付範囲が7日以内かチェックする
    if (end_date - start_date).days > 7:
        st.error("日付範囲は7日以内にしてください。")
        st.stop()

    # ぐるぐるのローディング表示をしながら処理を実行する
    with st.spinner("NASAのデータベースにアクセス中..."):
        try:
            # NASA APIから小惑星データを取得する
            data = fetch_neo_feed(nasa_key, start_date, end_date)
        except requests.exceptions.HTTPError as e:
            # HTTPエラー（APIキーが間違っている、レート制限など）のとき
            st.error(f"APIエラー: {e.response.status_code} - {e.response.text}")
            st.stop()
        except requests.exceptions.RequestException as e:
            # ネットワークエラーなど通信に問題があるとき
            st.error(f"通信エラー: {e}")
            st.stop()

    # 取得した小惑星の総数を表示する
    total = data.get("element_count", 0)
    st.metric("検出された小惑星の数", f"{total} 個")

    # 日付ごとに小惑星のリストを取り出して表示する
    neo_by_date = data.get("near_earth_objects", {})
    # AIに渡すためのサマリーテキストを作る
    summary_lines = []

    for date in sorted(neo_by_date.keys()):
        asteroids = neo_by_date[date]
        st.subheader(f"📅 {date}")

        for asteroid in asteroids:
            name = asteroid["name"]
            is_hazardous = asteroid["is_potentially_hazardous_asteroid"]
            # 推定直径（km）の最小・最大を取り出す
            diameter_min = asteroid["estimated_diameter"]["kilometers"]["estimated_diameter_min"]
            diameter_max = asteroid["estimated_diameter"]["kilometers"]["estimated_diameter_max"]
            # 最接近時のデータを取り出す（最初の要素を使う）
            approach = asteroid["close_approach_data"][0]
            miss_distance_km = float(approach["miss_distance"]["kilometers"])
            velocity_kph = float(approach["relative_velocity"]["kilometers_per_hour"])

            # 危険な小惑星は赤、安全な小惑星は青でラベルを付ける
            hazard_label = "🔴 潜在的に危険" if is_hazardous else "🔵 安全"

            # エクスパンダー（折りたたみUI）で各小惑星の詳細を表示する
            with st.expander(f"{hazard_label} | {name}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("推定直径", f"{diameter_min:.3f} 〜 {diameter_max:.3f} km")
                with col2:
                    st.metric("最接近距離", f"{miss_distance_km:,.0f} km")
                st.metric("相対速度", f"{velocity_kph:,.0f} km/h")

            # AIに渡すサマリーに追加する
            summary_lines.append(
                f"{name}: 直径 {diameter_min:.3f}〜{diameter_max:.3f}km, "
                f"接近距離 {miss_distance_km:,.0f}km, "
                f"速度 {velocity_kph:,.0f}km/h, "
                f"{'危険' if is_hazardous else '安全'}"
            )

    # AIに渡すサマリーを保存しておく
    neo_summary = "\n".join(summary_lines)

    # サマリーが保存されていればAI解説を表示する
    if neo_summary:
        with st.spinner("AIが小惑星データを解読中..."):
            # BedrockのAIに小惑星データを解説させる
            result = ask_bedrock(st.session_state['neo_summary'])
            st.success("🛸 AIによる解説")
            st.write(result)
