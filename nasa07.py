import streamlit as st  # ウェブアプリを作るためのライブラリ
import requests          # インターネット上のAPIにアクセスするためのライブラリ
import boto3             # AWSのサービスを使うためのライブラリ
import json              # データをJSON形式に変換するためのライブラリ

# ブラウザのタブに表示されるタイトルとアイコンを設定する
st.set_page_config(page_title="NASA Image Library", page_icon="📸")
# アプリの見出しを表示する
st.title("📸 NASA 画像・動画ライブラリ")

# 画面左側のサイドバーに検索条件の入力欄を作る
with st.sidebar:
    st.header("設定")
    # このAPIはAPIキーが不要であることを表示する
    st.info("このAPIはAPIキー不要です")
    # 検索キーワードを入力するテキストボックス
    query = st.text_input("検索キーワード", value="apollo")
    # 検索するメディアの種類を選ぶセレクトボックス
    media_type = st.selectbox("メディアタイプ", ["image", "video", "audio"],
                               format_func=lambda x: {"image": "画像", "video": "動画", "audio": "音声"}[x])

# 使い方の説明を青いボックスで表示する
st.info("キーワードを入力して『検索する』ボタンを押してみよう！")


def fetch_nasa_images(query, media_type):
    """NASAの画像・動画ライブラリAPIにリクエストを送り、キーワードで検索結果を取得する"""
    # APIのURL（q=検索キーワード、media_type=メディアの種類）
    url = f"https://images-api.nasa.gov/search?q={query}&media_type={media_type}&page_size=12"
    # URLにHTTPリクエストを送る
    response = requests.get(url)
    # エラー（404や429など）があれば例外を発生させる
    response.raise_for_status()
    # レスポンスの中にある検索結果アイテムのリストを返す
    return response.json().get("collection", {}).get("items", [])


def ask_bedrock(summary):
    """AWSのBedrockを通じてAIに検索結果を日本語でわかりやすく解説させる"""
    # BedrockのAPIクライアントを作成する
    bedrock = boto3.client(service_name='bedrock-runtime', region_name='ap-northeast-1')
    # AIへの指示文（プロンプト）を作る
    prompt = (
        f"以下はNASAの画像・動画ライブラリの検索結果です。"
        f"中高生が宇宙や科学に興味を持てるような親しみやすい日本語で、"
        f"検索結果の内容を200文字程度で紹介してください。\n\n{summary}"
    )
    # AIに送るデータをJSON形式に変換する
    body = json.dumps({"messages": [{"role": "user", "content": [{"text": prompt}]}]})
    # AIモデル（Amazon Nova Lite）を呼び出す
    response = bedrock.invoke_model(body=body, modelId="amazon.nova-lite-v1:0")
    # レスポンスのJSONを解析して、AIが生成したテキストを取り出す
    response_body = json.loads(response.get('body').read())
    return response_body['output']['message']['content'][0]['text']


# 「検索する」ボタンが押されたときの処理
if st.button("検索する"):
    # ぐるぐるのローディング表示をしながら処理を実行する
    with st.spinner("NASAのライブラリを検索中..."):
        try:
            # NASA画像ライブラリAPIから検索結果を取得する
            items = fetch_nasa_images(query, media_type)
        except requests.exceptions.HTTPError as e:
            # HTTPエラーのとき
            st.error(f"APIエラー: {e.response.status_code} - {e.response.text}")
            st.stop()
        except requests.exceptions.RequestException as e:
            # ネットワークエラーなど通信に問題があるとき
            st.error(f"通信エラー: {e}")
            st.stop()

    if not items:
        # 検索結果がなかったときのメッセージ
        st.warning("検索結果が見つかりませんでした。別のキーワードを試してみてください。")
    else:
        # 取得した検索結果の総数を表示する
        st.metric("検索結果", f"{len(items)} 件")

        # AIに渡すためのサマリーテキストを作る
        summary_lines = [f"検索キーワード: {query}"]

        # 3列のグリッドレイアウトで結果を表示する
        cols = st.columns(3)
        for i, item in enumerate(items):
            # メタデータ（タイトル・説明・日付）を取り出す
            data = item.get("data", [{}])[0]
            title = data.get("title", "タイトルなし")
            description = data.get("description", "説明なし")
            date_created = data.get("date_created", "")[:10]  # YYYY-MM-DD形式に切り取る

            # サムネイル画像のURLを取り出す（linksリストの最初のもの）
            links = item.get("links", [])
            thumb_url = links[0]["href"] if links else None

            # 表示する列を順番に切り替える（0→1→2→0→1...）
            col = cols[i % 3]
            with col:
                # サムネイル画像を表示する（画像のみ）
                if thumb_url and media_type == "image":
                    st.image(thumb_url, use_container_width=True)
                # タイトルを表示する
                st.caption(f"**{title}**")
                # 詳細な説明文を折りたたみUIで表示する
                with st.expander("説明を見る"):
                    st.write(description)
                    if date_created:
                        st.write(f"公開日: {date_created}")

            # AIに渡すサマリーに追加する
            summary_lines.append(f"・{title} ({date_created})")

        # AIに渡すサマリーをセッションに保存しておく
        st.session_state['image_summary'] = "\n".join(summary_lines)

# サマリーが保存されているときだけAI解説ボタンを表示する
if 'image_summary' in st.session_state:
    if st.button("AIに検索結果を解説してもらう"):
        with st.spinner("AIが検索結果を解読中..."):
            # BedrockのAIに検索結果を解説させる
            result = ask_bedrock(st.session_state['image_summary'])
            st.success("🔭 AIによる解説")
            st.write(result)
