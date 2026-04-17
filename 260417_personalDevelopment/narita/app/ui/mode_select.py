import streamlit as st


def render_mode_select() -> str:
    return st.radio("モードを選択してください", ["フォーマット登録機能", "文字認識機能"], horizontal=True)
