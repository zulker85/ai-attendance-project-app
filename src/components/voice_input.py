import streamlit as st


_AUDIO_TYPES = ["wav", "mp3", "ogg", "webm", "m4a"]


def voice_input(label, *, key, disabled=False):
    input_method = st.radio(
        "Voice input method",
        ("Live microphone", "Upload audio file"),
        horizontal=True,
        key=f"{key}_method",
        disabled=disabled,
        help=(
            "Use Live microphone for a fresh voice check. Choose Upload audio "
            "file if the browser blocks microphone access."
        ),
    )

    if input_method == "Live microphone":
        st.caption(
            f"{label}. Allow microphone access when your browser asks, then "
            "stop recording when you finish."
        )
        return st.audio_input(
            label,
            sample_rate=16000,
            key=key,
            disabled=disabled,
            help="Record a clear voice sample of at least one second.",
        )

    st.caption(
        f"{label}. Upload a clear recording of at least one second "
        "(WAV, MP3, OGG, WEBM, or M4A)."
    )
    return st.file_uploader(
        "Choose an audio file",
        type=_AUDIO_TYPES,
        key=f"{key}_upload",
        disabled=disabled,
        help="Microphone recording is unavailable in this browser session.",
    )
