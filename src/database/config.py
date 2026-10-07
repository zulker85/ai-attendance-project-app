import streamlit as st


from supabase import create_client, Client

supabase_key = st.secrets["SUPABASE_KEY"]
if supabase_key.startswith("sb_publishable_"):
    raise RuntimeError(
        "SUPABASE_KEY is a publishable key. Configure a Supabase server-side "
        "secret/service_role key in Streamlit secrets; voice attendance RPCs "
        "are intentionally restricted to service_role."
    )

supabase: Client = create_client(
    st.secrets["SUPABASE_URL"],
    supabase_key
)