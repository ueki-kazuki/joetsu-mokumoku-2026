import streamlit as st  # ウェブアプリを作るためのライブラリ

# ブラウザのタブに表示されるタイトルとアイコンを設定する
st.set_page_config(
    page_title="NASA 宇宙探検ダッシュボード",
    page_icon="🚀",
    layout="wide",  # 画面全体を使うワイドレイアウトにする
)

# 各ページをnasa01〜08.pyファイルと対応付ける
pages = st.navigation([
    st.Page("bedrock_check.py", title="Bedrock 接続確認",          icon="🔌"),
    st.Page("nasa01.py", title="今日の宇宙画像（APOD）",        icon="🌌"),
    st.Page("nasa02.py", title="小惑星接近（NeoWs）",          icon="☄️"),
    st.Page("nasa03.py", title="宇宙天気（DONKI）",             icon="🌞"),
    st.Page("nasa04.py", title="自然災害トラッカー（EONET）",   icon="🌍"),
    st.Page("nasa05.py", title="地球まるごとビューア（EPIC）",  icon="🌏"),
    st.Page("nasa06.py", title="火星探査ローバー",              icon="🔴"),
    st.Page("nasa07.py", title="NASA 画像・動画ライブラリ",     icon="📸"),
    st.Page("nasa08.py", title="衛星画像（Landsat）",          icon="🛰️"),
])

# ナビゲーションを実行し、選択されたページを表示する
pages.run()
