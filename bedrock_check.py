import streamlit as st
import boto3
import json

st.set_page_config(page_title="Bedrock 接続確認", page_icon="🔌")
st.title("🔌 Amazon Bedrock 接続確認")
st.write("nasa01.py を実行する前に、Bedrock が正しく設定されているか確認します。")

# --- 1. AWS 認証情報の確認 ---
st.header("Step 1: AWS 認証情報の確認")

try:
    session = boto3.session.Session()
    credentials = session.get_credentials()
    region = session.region_name

    if credentials is None:
        st.error("AWS 認証情報が見つかりません。`aws configure` を実行してください。")
    else:
        creds = credentials.get_frozen_credentials()
        masked_key = creds.access_key[:4] + "****" if creds.access_key else "(なし)"
        st.success("AWS 認証情報が見つかりました。")
        col1, col2 = st.columns(2)
        col1.metric("Access Key ID (先頭4文字)", masked_key)
        col2.metric("リージョン", region or "(未設定)")

        if not region:
            st.warning("リージョンが設定されていません。`aws configure` でリージョンを設定してください。")

except Exception as e:
    st.error(f"認証情報の読み込みに失敗しました: {e}")

st.divider()

# --- 2. Bedrock モデルの呼び出しテスト ---
st.header("Step 2: Bedrock 接続テスト")
st.write("ボタンを押すと、Amazon Nova Lite に「こんにちは」と送信して応答を確認します。")

if st.button("Bedrock に接続してテストする"):
    with st.spinner("Bedrock に接続中..."):
        try:
            bedrock = boto3.client(service_name="bedrock-runtime", region_name="ap-northeast-1")
            body = json.dumps({
                "messages": [
                    {"role": "user", "content": [{"text": "こんにちは。1文で自己紹介してください。"}]}
                ]
            })
            response = bedrock.invoke_model(body=body, modelId="amazon.nova-lite-v1:0")
            response_body = json.loads(response.get("body").read())
            reply = response_body["output"]["message"]["content"][0]["text"]

            st.success("Bedrock への接続に成功しました！")
            st.info(f"AIからの返答: {reply}")

        except bedrock.exceptions.AccessDeniedException:
            st.error("アクセス拒否エラー: Bedrock へのアクセス権限がありません。IAM ポリシーを確認してください。")
        except bedrock.exceptions.ResourceNotFoundException:
            st.error("モデルが見つかりません。Bedrock のコンソールで `amazon.nova-lite-v1:0` が有効になっているか確認してください。")
        except Exception as e:
            st.error(f"Bedrock 接続エラー: {e}")

st.divider()

# --- 3. 確認チェックリスト ---
st.header("Step 3: 確認チェックリスト")
st.write("問題がある場合は以下を確認してください。")

st.markdown("""
| 確認項目 | 方法 |
|---|---|
| AWS CLI がインストールされている | ターミナルで `aws --version` |
| 認証情報が設定されている | ターミナルで `aws configure list` |
| リージョンが `ap-northeast-1` に設定されている | ターミナルで `aws configure list` |
| Bedrock でモデルアクセスが有効になっている | [AWS コンソール > Bedrock > モデルアクセス](https://ap-northeast-1.console.aws.amazon.com/bedrock/home?region=ap-northeast-1#/modelaccess) |
| IAM ユーザーに `bedrock:InvokeModel` 権限がある | [AWS コンソール > IAM](https://console.aws.amazon.com/iam/) |
""")

st.success("すべて確認できたら nasa01.py に進みましょう！")
