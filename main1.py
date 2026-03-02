import streamlit as st
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import openai

# ========================================================
# 实验员控制台 (仅在此处修改参数即可切换实验组)
# ========================================================
EXPERIMENTAL_GROUP = "HIGH_CONFIDENCE"  # 当前固定为高自信组
ENABLE_HALLUCINATION = False  # False: 准确组 | True: 幻觉组 (20%错误率)
# ========================================================

# API 配置
DEEPSEEK_API_KEY = "sk-46f5736e30f544288284d6b7d7641393"
ELEVENLABS_API_KEY = "sk_82eea299b22d291c4703e32ee9fa49685ce8e62e91b1ebf9"

# 语音特征配置 (高自信组)
VOICE_ID = "KrFd1FTEPvldJW044qa2"
STABILITY_VAL = 0.85  # 高稳定性表现权威感

client_ds = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
client_el = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# --- 1. 样式定制 ---
st.set_page_config(page_title="语音交互评估系统", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #f3f3f3; }
    header { visibility: hidden; }
    .fixed-header {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: #ededed; padding: 12px;
        text-align: center; font-weight: bold;
        border-bottom: 1px solid #dcdcdc; z-index: 1000; font-size: 16px;
    }
    .chat-container { padding-top: 60px; padding-bottom: 150px; }

    /* 微信气泡样式 */
    [data-testid="stChatMessageAssistant"] { flex-direction: row !important; }
    [data-testid="stChatMessageAssistant"] .st-ed {
        background-color: #ffffff !important; border-radius: 6px !important;
        border: 1px solid #e5e5e5 !important; color: #000 !important;
    }
    [data-testid="stChatMessageUser"] { flex-direction: row-reverse !important; }
    [data-testid="stChatMessageUser"] .st-ed {
        background-color: #95ec69 !important; border-radius: 6px !important; color: #000 !important;
    }

    .fixed-footer {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #f7f7f7; padding: 20px;
        border-top: 1px solid #dcdcdc; z-index: 1000;
    }
    </style>
    <div class="fixed-header">语音交互评估系统</div>
    """, unsafe_allow_html=True)

# --- 2. 逻辑初始化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. 渲染聊天历史 ---
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "audio" in msg:
            st.markdown("---")
            st.caption("🔊 语音回复")
            st.audio(msg["audio"], format="audio/mp3")
st.markdown('</div>', unsafe_allow_html=True)

# --- 4. 底部输入区 ---
with st.container():
    st.markdown('<div class="fixed-footer">', unsafe_allow_html=True)
    col_sel, col_btn = st.columns([4, 1])

    preset_questions = [
        "请选择您想要询问的问题...",
        "家庭如何通过节能减排来减少碳排放？",
        "什么是绿色环保理念？",
        "室内植物对空气净化的作用"
    ]

    selected_option = col_sel.selectbox("Q", preset_questions, label_visibility="collapsed")
    send_trigger = col_btn.button("发送", use_container_width=True, type="primary")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. 交互逻辑 ---
if send_trigger and selected_option != "请选择您想要询问的问题...":
    st.session_state.messages.append({"role": "user", "content": selected_option})
    st.rerun()

if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
    last_user_msg = st.session_state.messages[-1]["content"]

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("*(正在生成回复...)*")

        try:
            # 根据实验员设置决定 Prompt
            if ENABLE_HALLUCINATION:
                # 幻觉组：混合错误事实，但语气坚定
                system_prompt = (
                    "你是一个助手。回答100字以内，采用连贯段落。核心要求：在回答中故意混入约20%的常识性错误（例如错误的数值或因果关系），"
                    "但必须使用极其确定、果断、不容置疑的口吻表述。"
                )
                temp = 1.3
            else:
                # 准确组：严谨准确
                system_prompt = "你是一个严谨专业的助手。回答必须在100字以内，采用连贯段落，确保事实100%准确，不准分点。"
                temp = 0.3

            # 1. 文本生成
            response = client_ds.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": last_user_msg}],
                temperature=temp
            )
            answer_text = response.choices[0].message.content

            # 2. 语音生成 (固定为高自信组参数)
            audio_gen = client_el.text_to_speech.convert(
                voice_id=VOICE_ID,
                text=answer_text,
                model_id="eleven_multilingual_v2",
                voice_settings=VoiceSettings(
                    stability=STABILITY_VAL,
                    similarity_boost=0.8,
                    use_speaker_boost=True
                )
            )
            audio_bytes = b"".join(list(audio_gen))

            # 3. 更新状态
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer_text,
                "audio": audio_bytes
            })
            st.rerun()

        except Exception as e:
            placeholder.empty()
            st.error("系统连接超时，请重试。")