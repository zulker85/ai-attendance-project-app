import hashlib
from io import BytesIO

import streamlit as st
from PIL import Image


@st.dialog("Capture or upload photos")
def add_photos_dialog():

    st.write(
        'Add one or more classroom photos. For crowded rooms, use clear, well-lit '
        'photos from different parts of the room so faces are larger and unobstructed.'
    )

    if 'photo_tab' not in st.session_state:
        st.session_state.photo_tab = 'camera'
    if 'attendance_image_keys' not in st.session_state:
        st.session_state.attendance_image_keys = set()

    t1, t2 = st.columns(2)

    with t1:
        type_camera = "primary" if st.session_state.photo_tab == 'camera' else 'tertiary'
        if st.button('Camera', type=type_camera, width='stretch'):
            st.session_state.photo_tab = 'camera'



    with t2:
        type_upload = "primary" if st.session_state.photo_tab == 'upload' else 'tertiary'
        if st.button('Upload photos', type=type_upload, width='stretch'):
            st.session_state.photo_tab = 'upload'

    if st.session_state.photo_tab == 'camera':
        cam_photo = st.camera_input('Take Snapshot', key='dialog_cam')
        if cam_photo:
            image_bytes = cam_photo.getvalue()
            image_key = hashlib.sha256(image_bytes).hexdigest()
            if image_key not in st.session_state.attendance_image_keys:
                st.session_state.attendance_images.append(
                    Image.open(BytesIO(image_bytes)).copy()
                )
                st.session_state.attendance_image_keys.add(image_key)
                st.toast('Photo Captured')


    if st.session_state.photo_tab == 'upload':
        uploaded_files = st.file_uploader( 'choose image files', type=['jpg', 'png', 'jpeg' ], accept_multiple_files=True, key='dialog_upload')

        if uploaded_files:
            added_photo = False
            for f in uploaded_files:
                image_bytes = f.getvalue()
                image_key = hashlib.sha256(image_bytes).hexdigest()
                if image_key not in st.session_state.attendance_image_keys:
                    st.session_state.attendance_images.append(
                        Image.open(BytesIO(image_bytes)).copy()
                    )
                    st.session_state.attendance_image_keys.add(image_key)
                    added_photo = True

            if added_photo:
                st.toast('Photo Uploaded Successfully')

    st.divider()
    if st.button('Done', type='primary', width='stretch'):
        st.rerun()
