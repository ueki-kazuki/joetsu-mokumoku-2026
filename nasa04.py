import streamlit as st  # ウェブアプリを作るためのライブラリ
import requests          # インターネット上のAPIにアクセスするためのライブラリ
import boto3             # AWSのサービスを使うためのライブラリ
import json              # データをJSON形式に変換するためのライブラリ
import pandas as pd      # 地図表示のためにデータを整形するライブラリ

# ブラウザのタブに表示されるタイトルとアイコンを設定する
st.set_page_config(page_title="NASA EONET Dashboard", page_icon="🌍")
# アプリの見出しを表示する
st.title("🌍 NASA 地球自然災害トラッカー")

# 画面左側のサイドバーにカテゴリと状態の選択欄を作る
with st.sidebar:
    st.header("設定")
    # このAPIはAPIキー不要だが、他のファイルと統一するために入力欄を置く
    st.text_input("NASA API Key（このAPIは不要）", value="DEMO_KEY", type="password", disabled=True)
    # 表示するカテゴリを選ぶセレクトボックス
    category_options = {
        "すべて": "",
        "山火事": "wildfires",
        "暴風雨": "severeStorms",
        "火山": "volcanoes",
        "洪水": "floods",
        "地震": "earthquakes",
        "海氷・湖氷": "seaLakeIce",
    }
    selected_category_label = st.selectbox("カテゴリを選択", list(category_options.keys()))
    selected_category = category_options[selected_category_label]
    # 表示する状態を選ぶラジオボタン
    status = st.radio("状態", ["open", "closed", "all"], format_func=lambda x: {"open": "進行中", "closed": "終了", "all": "すべて"}[x])

# 使い方の説明を青いボックスで表示する
st.info("カテゴリと状態を選んで『自然災害を調べる』ボタンを押してみよう！")


def fetch_eonet_events(status, category):
    """NASAのEONET APIにリクエストを送り、地球上で起きている自然災害イベントを取得する"""
    # ベースとなるAPIのURL
    url = f"https://eonet.gsfc.nasa.gov/api/v3/events?limit=30&status={status}"
    # カテゴリが指定されているときはURLに追加する
    if category:
        url += f"&category={category}"
    # URLにHTTPリクエストを送る
    response = requests.get(url)
    # エラー（404や429など）があれば例外を発生させる
    response.raise_for_status()
    # レスポンスの中にある「events」リストを返す
    return response.json().get("events", [])


def ask_bedrock(summary):
    """AWSのBedrockを通じてAIに自然災害データを日本語でわかりやすく解説させる"""
    # BedrockのAPIクライアントを作成する
    bedrock = boto3.client(service_name='bedrock-runtime', region_name='ap-northeast-1')
    # AIへの指示文（プロンプト）を作る
    prompt = (
        f"以下は地球で発生している自然災害の観測データです。"
        f"中高生が地球環境への関心を持てるような親しみやすい日本語で、"
        f"現在の状況を200文字程度で解説してください。\n\n{summary}"
    )
    # AIに送るデータをJSON形式に変換する
    body = json.dumps({"messages": [{"role": "user", "content": [{"text": prompt}]}]})
    # AIモデル（Amazon Nova Lite）を呼び出す
    response = bedrock.invoke_model(body=body, modelId="amazon.nova-lite-v1:0")
    # レスポンスのJSONを解析して、AIが生成したテキストを取り出す
    response_body = json.loads(response.get('body').read())
    return response_body['output']['message']['content'][0]['text']


# 「自然災害を調べる」ボタンが押されたときの処理
if st.button("自然災害を調べる"):
    # ぐるぐるのローディング表示をしながら処理を実行する
    with st.spinner("NASAのデータベースにアクセス中..."):
        try:
            # EONET APIから自然災害イベントを取得する
            events = fetch_eonet_events(status, selected_category)
        except requests.exceptions.HTTPError as e:
            # HTTPエラーのとき
            st.error(f"APIエラー: {e.response.status_code} - {e.response.text}")
            st.stop()
        except requests.exceptions.RequestException as e:
            # ネットワークエラーなど通信に問題があるとき
            st.error(f"通信エラー: {e}")
            st.stop()

    # 取得した自然災害イベントの総数を表示する
    st.metric("検出されたイベント数", f"{len(events)} 件")

    if not events:
        # イベントがなかったときのメッセージ
        st.info("該当するイベントはありませんでした。")
    else:
        # 地図に表示するための座標データを集める
        map_data = []
        # AIに渡すためのサマリーテキストを作る
        summary_lines = []

        for event in events:
            title = event.get("title", "不明")
            # カテゴリ名を取り出す（リストの最初の要素を使う）
            categories = [c["title"] for c in event.get("categories", [])]
            category_str = ", ".join(categories)
            # 最新の観測データを取り出す（リストの最後の要素を使う）
            geometries = event.get("geometry", [])
            latest = geometries[-1] if geometries else {}
            date = latest.get("date", "不明")
            coords = latest.get("coordinates")  # [経度, 緯度] の順番

            # エクスパンダー（折りたたみUI）で各イベントの詳細を表示する
            with st.expander(f"🔴 {title} ({category_str})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**カテゴリ:** {category_str}")
                    st.write(f"**最終観測日時:** {date}")
                with col2:
                    if coords:
                        # 経度・緯度を表示する（EONETは[経度, 緯度]の順なので注意）
                        st.write(f"**緯度:** {coords[1]:.4f}")
                        st.write(f"**経度:** {coords[0]:.4f}")
                # NASAの詳細ページへのリンクを表示する
                if event.get("link"):
                    st.markdown(f"[NASAの詳細ページを見る]({event['link']})")

            # 座標があれば地図用データに追加する（EONETは[経度, 緯度]なのでlatとlonを入れ替える）
            if coords:
                map_data.append({"lat": coords[1], "lon": coords[0]})

            # AIに渡すサマリーに追加する
            summary_lines.append(f"{title} ({category_str}): {date}")

        # 座標データがあれば地図に表示する
        if map_data:
            st.subheader("🗺️ イベント発生マップ")
            st.map(pd.DataFrame(map_data))

        # AIに渡すサマリーをセッションに保存しておく
        st.session_state['eonet_summary'] = "\n".join(summary_lines)

# サマリーが保存されているときだけAI解説ボタンを表示する
if 'eonet_summary' in st.session_state:
    if st.button("AIに自然災害を解説してもらう"):
        with st.spinner("AIが災害データを解読中..."):
            # BedrockのAIに自然災害データを解説させる
            result = ask_bedrock(st.session_state['eonet_summary'])
            st.success("🌏 AIによる解説")
            st.write(result)
