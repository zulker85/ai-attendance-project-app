import streamlit as st



def style_background_home():

    st.markdown("""
        <style>

                .stApp {
                    background: #5865F2 !important;
                }

                .stApp div[data-testid="stColumn"]{
                    background-color:#E0E3FF !important;
                    padding:2.5rem !important;
                    border-radius: 5rem !important;
                    }

                .stApp div[data-testid="stColumn"] h2 {
                    color: #000 !important;
                }
        </style>  

                """
            ,unsafe_allow_html=True)
    

def style_background_dashboard():

    st.markdown("""
        <style>

                .stApp {
                    background: #E0E3FF !important;
                    color: #000 !important;
                }

                .stApp h1,
                .stApp h2,
                .stApp [data-testid="stSpinner"] p {
                    color: #000 !important;
                }

                    .stApp [data-testid="stAlert"] p,
                    .stApp [data-testid="stAlert"] span,
                    .stApp [data-testid="stFileUploader"] label,
                    .stApp [data-testid="stFileUploader"] small,
                    .stApp [data-testid="stCaptionContainer"] p {
                        color: #111827 !important;
                    }

                    .stApp [data-testid="stAlert"] {
                        border: 1px solid #374151 !important;
                        font-weight: 600 !important;
                    }

                    .stApp [data-testid="stException"] {
                        background: #fff7ed !important;
                        color: #111827 !important;
                        border: 2px solid #c2410c !important;
                        border-radius: 0.75rem !important;
                        padding: 1rem !important;
                    }

                    .stApp [data-testid="stException"] * {
                        color: #111827 !important;
                    }

                    .stApp [data-testid="stFileUploader"] section,
                    .stApp [data-testid="stFileUploaderDropzone"],
                    .stApp [data-testid="stAudioInput"] {
                        background: #ffffff !important;
                        color: #111827 !important;
                        border: 1px solid #64748b !important;
                    }

                    .stApp [data-testid="stFileUploader"] section *,
                    .stApp [data-testid="stFileUploaderDropzone"] *,
                    .stApp [data-testid="stAudioInput"] * {
                        color: #111827 !important;
                    }

                    .stApp [data-testid="stFileUploader"] button,
                    .stApp [data-testid="stAudioInput"] button {
                        background: #5865f2 !important;
                        color: #ffffff !important;
                    }
        </style>  

                """
            ,unsafe_allow_html=True)
    

    

def style_base_layout():
# asdasd
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Climate+Crisis:YEAR@1979&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@100..900&display=swap');

                
         /* Hide Top Bar of streamlit */
                
            #MainMenu, footer, header {
                visibility: hidden;
            }

            [data-testid="stExpander"] details[open] > summary,
            [data-testid="stExpander"] details[open] [data-testid="stExpanderDetails"] {
                background-color: #fff !important;
                color: #000 !important;
            }

            [data-testid="stExpander"] details[open] > summary [data-testid="stMarkdownContainer"],
            [data-testid="stExpander"] details[open] > summary [data-testid="stMarkdownContainer"] * {
                color: #000 !important;
            }

            .block-container {
                padding-top:1.5rem !important;    
            }

            h1 {
                font-family: 'Climate Crisis', sans-serif !important;
                font-size: 3.5rem !important;
                line-height:1.1 1important;
                margin-bottom:0rem !important;
            }
                

            h2 {
                font-family: 'Climate Crisis', sans-serif !important;
                font-size: 2rem !important;
                line-height:0.9 !important;
                margin-bottom:0rem !important;
            }
                
            h3, h4, p {
                font-family: 'Outfit', sans-serif;    
            }
                

            button{
                border-radius: 1.5rem !important;
                background-color: #5865F2 !important;
                color: white !important;
                padding: 10px 20px !important;
                border: none !important;
                transition: transform 0.25s ease-in-out !important;
                }

            button[kind="secondary"]{
                border-radius: 1.5rem !important;
                background-color: #EB459E !important;
                color: white !important;
                padding: 10px 20px !important;
                border: none !important;
                transition: transform 0.25s ease-in-out !important;
                }

            button[kind="tertiary"]{
                border-radius: 1.5rem !important;
                background-color: black !important;
                color: white !important;
                padding: 10px 20px !important;
                border: none !important;
                transition: transform 0.25s ease-in-out !important;
                }

            button:disabled {
                opacity: 0.45 !important;
                cursor: not-allowed !important;
                transform: none !important;
            }

            button:not(:disabled):hover {
                transform: scale(1.03);
            }
        </style>  

                """
            ,unsafe_allow_html=True)