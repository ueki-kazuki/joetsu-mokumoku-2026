import streamlit as st  # ウェブアプリを作るためのライブラリ
import requests          # インターネット上のAPIにアクセスするためのライブラリ
import boto3             # AWSのサービスを使うためのライブラリ
import json              # データをJSON形式に変換するためのライブラリ
from datetime import timedelta  # 日付の計算に使うライブラリ

# ブラウザのタブに表示されるタイトルとアイコンを設定する
st.set_page_config(page_title="NASA DONKI Dashboard", page_icon="🌞")
# アプリの見出しを表示する
st.title("🌞 NASA 宇宙天気ダッシュボード")

# 画面左側のサイドバーにAPIキーと日付の入力欄を作る
with st.sidebar:
    st.header("設定")
    # NASAのAPIキーを入力するテキストボックス（デフォルトはDEMO_KEY）
    nasa_key = st.text_input("NASA API Keyを入力", value="DEMO_KEY", type="password")
    # 検索開始日を選ぶカレンダーUI
    start_date = st.date_input("開始日")
    # 検索終了日（デフォルトは開始日から7日後）
    end_date = st.date_input("終了日", value=start_date + timedelta(days=7))

# 使い方の説明を青いボックスで表示する
st.info("日付範囲を選んで『宇宙天気を調べる』ボタンを押してみよう！")


def fetch_donki_cme(api_key, start_date, end_date):
    """NASAのDONKI APIにリクエストを送り、指定期間のコロナ質量放出（CME）イベントを取得する"""
    # APIのURL（startDate・endDate・api_keyをパラメータとして渡す）
    url = (
        f"https://api.nasa.gov/DONKI/CME"
        f"?startDate={start_date}&endDate={end_date}&api_key={api_key}"
    )
    # URLにHTTPリクエストを送る
    response = requests.get(url)
    # エラー（404や429など）があれば例外を発生させる
    response.raise_for_status()
    # レスポンスをJSON形式（リスト型）に変換して返す
    return response.json()


def ask_bedrock(summary):
    """AWSのBedrockを通じてAIに宇宙天気データを日本語でわかりやすく解説させる"""
    # BedrockのAPIクライアントを作成する
    bedrock = boto3.client(service_name='bedrock-runtime', region_name='ap-northeast-1')
    # AIへの指示文（プロンプト）を作る
    prompt = (
        f"以下は太陽から放出されたコロナ質量放出（CME）の観測データです。"
        f"中高生がワクワクするような親しみやすい日本語で、"
        f"太陽活動の様子を200文字程度で解説してください。\n\n{summary}"
    )
    # AIに送るデータをJSON形式に変換する
    body = json.dumps({"messages": [{"role": "user", "content": [{"text": prompt}]}]})
    # AIモデル（Amazon Nova Lite）を呼び出す
    response = bedrock.invoke_model(body=body, modelId="amazon.nova-lite-v1:0")
    # レスポンスのJSONを解析して、AIが生成したテキストを取り出す
    response_body = json.loads(response.get('body').read())
    return response_body['output']['message']['content'][0]['text']


# 「宇宙天気を調べる」ボタンが押されたときの処理
if st.button("宇宙天気を調べる"):
    # ぐるぐるのローディング表示をしながら処理を実行する
    with st.spinner("NASAのデータベースにアクセス中..."):
        try:
            # DONKI APIからCMEイベントを取得する
            events = fetch_donki_cme(nasa_key, start_date, end_date)
        except requests.exceptions.HTTPError as e:
            # HTTPエラー（APIキーが間違っている、レート制限など）のとき
            st.error(f"APIエラー: {e.response.status_code} - {e.response.text}")
            st.stop()
        except requests.exceptions.RequestException as e:
            # ネットワークエラーなど通信に問題があるとき
            st.error(f"通信エラー: {e}")
            st.stop()

    # 取得したCMEイベントの総数を表示する
    st.metric("検出されたCMEイベント数", f"{len(events)} 件")

    if not events:
        # イベントがなかったときのメッセージ
        st.info("この期間にCMEイベントはありませんでした。")
    else:
        # AIに渡すためのサマリーテキストを作る
        summary_lines = []

        for event in events:
            # イベントIDと開始時刻を取り出す
            activity_id = event.get("activityID", "不明")
            start_time = event.get("startTime", "不明")
            source = event.get("sourceLocation", "不明")
            note = event.get("note", "解説なし")

            # 最も精度の高いCME解析データを取り出す（リストの最初のものを使う）
            analyses = event.get("cmeAnalyses", [])
            speed = None
            kp_index = None
            is_earth_impact = False
            if analyses:
                # 最も精度の高い解析結果を探す
                best = next((a for a in analyses if a.get("isMostAccurate")), analyses[0])
                speed = best.get("speed")
                # 地球への影響予測リストを確認する
                for enlil in best.get("enlilList", []):
                    if enlil.get("isEarthGB"):
                        is_earth_impact = True
                        kp_index = enlil.get("kp_180")
                        break

            # 地球への影響の有無でラベルを切り替える
            impact_label = "🌍 地球に影響あり" if is_earth_impact else "🌌 地球への影響なし"

            # エクスパンダー（折りたたみUI）で各イベントの詳細を表示する
            with st.expander(f"{impact_label} | {start_time} ({source})"):
                col1, col2 = st.columns(2)
                with col1:
                    # CMEの速度を表示する（データがあれば）
                    st.metric("CME速度", f"{speed} km/s" if speed else "不明")
                with col2:
                    # 地磁気活動の指数（Kpインデックス）を表示する
                    st.metric("Kpインデックス予測", str(kp_index) if kp_index else "なし")
                # NASAによる詳細な解説文を表示する
                st.caption("NASAによるメモ:")
                st.write(note)
                # 詳細ページへのリンクを表示する
                if event.get("link"):
                    st.markdown(f"[NASAの詳細ページを見る]({event['link']})")

            # AIに渡すサマリーに追加する
            summary_lines.append(
                f"{start_time} 発生, 発生位置: {source}, "
                f"速度: {speed} km/s, "
                f"地球影響: {'あり (Kp=' + str(kp_index) + ')' if is_earth_impact else 'なし'}"
            )

        # AIに渡すサマリーをセッションに保存しておく
        st.session_state['donki_summary'] = "\n".join(summary_lines)

# サマリーが保存されているときだけAI解説ボタンを表示する
if 'donki_summary' in st.session_state:
    if st.button("AIに宇宙天気を解説してもらう"):
        with st.spinner("AIが太陽活動データを解読中..."):
            # BedrockのAIにCMEデータを解説させる
            result = ask_bedrock(st.session_state['donki_summary'])
            st.success("☀️ AIによる解説")
            st.write(result)
