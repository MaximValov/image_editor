import streamlit as st
from PIL import Image
import io
import numpy as np
from rembg import remove
import matplotlib.pyplot as plt
import os
from io import BytesIO

# Initialize session state
if 'drawings' not in st.session_state:
    st.session_state.drawings = []
if 'current_tool' not in st.session_state:
    st.session_state.current_tool = "select"
if 'bg_removed_image' not in st.session_state:
    st.session_state.bg_removed_image = None
if 'original_image' not in st.session_state:
    st.session_state.original_image = None
if 'active_image' not in st.session_state:
    st.session_state.active_image = None
if 'start_point' not in st.session_state:
    st.session_state.start_point = None
if 'fig' not in st.session_state:
    st.session_state.fig = None
if 'original_filename' not in st.session_state:
    st.session_state.original_filename = None


def main():
    st.title("🎨 Professional Image Editor")
    st.write("Upload, edit, and measure images")

    # Sidebar controls
    st.sidebar.header("Tools")
    uploaded_file = st.sidebar.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        try:
            # Read and verify image
            image = verify_and_convert_image(uploaded_file)
            if image is None:
                st.error("Invalid image file")
                return
            st.session_state.original_filename = os.path.splitext(uploaded_file.name)[0]

            st.session_state.original_image = image
            st.session_state.active_image = image.copy()

            # Display original in sidebar
            st.sidebar.image(image, caption="Original Image", use_column_width=True)

            # AI Background Removal
            if st.sidebar.button("Remove Background"):
                with st.spinner("Removing background..."):
                    try:
                        st.session_state.bg_removed_image = remove(image)
                        st.session_state.active_image = st.session_state.bg_removed_image
                        st.sidebar.image(st.session_state.bg_removed_image,
                                         caption="Background Removed",
                                         use_column_width=True)
                    except Exception as e:
                        st.error(f"Background removal failed: {str(e)}")

            # Tool selection
            st.session_state.current_tool = st.sidebar.radio(
                "Annotation Tools:",
                ["select", "line", "measure"],
                index=0
            )

            color = st.sidebar.color_picker("Drawing Color", "#FF0000")
            line_width = st.sidebar.slider("Line Width", 1, 10, 2)

            if st.sidebar.button("Clear All Annotations"):
                st.session_state.drawings = []
                st.session_state.start_point = None

            # Display image with annotations
            display_image_with_drawing_tools()

            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save Image with Annotations"):
                    img_bytes = get_annotated_image()
                    if img_bytes:
                        st.download_button(
                            label="Download Annotated Image",
                            data=img_bytes,
                            file_name="annotated_image.png",
                            mime="image/png"
                        )

            with col2:
                if st.session_state.bg_removed_image is not None:
                    buffered = BytesIO()
                    st.session_state.bg_removed_image.save(buffered, format="PNG")
                    st.download_button(
                        label="Download BG-Removed Image",
                        data=buffered.getvalue(),
                        file_name=f"{st.session_state.original_filename}_bg_removed.png",
                        mime="image/png"
                    )

        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
            reset_session_state()


def verify_and_convert_image(uploaded_file):
    """Verify and convert image to RGB format"""
    try:
        image = Image.open(uploaded_file)
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        return image
    except Exception as e:
        st.error(f"Invalid image file: {str(e)}")
        return None


def display_image_with_drawing_tools():
    """Display image with drawing tools"""
    try:
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.imshow(st.session_state.active_image)
        ax.axis('off')

        # Draw existing annotations
        for drawing in st.session_state.drawings:
            if drawing['type'] == 'line':
                line = plt.Line2D(
                    [drawing['x0'], drawing['x1']],
                    [drawing['y0'], drawing['y1']],
                    color=drawing['color'],
                    linewidth=drawing['width']
                )
                ax.add_line(line)

                if drawing.get('measure', False):
                    # Add measurement text
                    mid_x = (drawing['x0'] + drawing['x1']) / 2
                    mid_y = (drawing['y0'] + drawing['y1']) / 2
                    distance = ((drawing['x1'] - drawing['x0']) ** 2 + (drawing['y1'] - drawing['y0']) ** 2) ** 0.5
                    ax.text(
                        mid_x, mid_y, f"{distance:.1f} px",
                        color=drawing['color'], fontsize=12,
                        bbox=dict(facecolor='white', alpha=0.8, edgecolor='none')
                    )

        st.pyplot(fig)

        # Coordinate selection for drawing
        st.write("Set coordinates for measurements:")
        col1, col2 = st.columns(2)
        with col1:
            x = st.slider("X", 0, st.session_state.active_image.width, st.session_state.active_image.width // 2)
        with col2:
            y = st.slider("Y", 0, st.session_state.active_image.height, st.session_state.active_image.height // 2)

        if st.button("Add Point"):
            handle_point_addition(x, y)

    except Exception as e:
        st.error(f"Display error: {str(e)}")


def handle_point_addition(x, y):
    """Handle adding measurement points"""
    if st.session_state.current_tool in ["line", "measure"]:
        if st.session_state.start_point is None:
            st.session_state.start_point = (x, y)
            st.success(f"Start point set at ({x}, {y})")
        else:
            # Complete the line
            x0, y0 = st.session_state.start_point
            st.session_state.drawings.append({
                'type': 'line',
                'x0': x0,
                'y0': y0,
                'x1': x,
                'y1': y,
                'color': st.session_state.get('color', '#FF0000'),
                'width': st.session_state.get('line_width', 2),
                'measure': (st.session_state.current_tool == "measure")
            })
            st.session_state.start_point = None
            st.experimental_rerun()


def get_annotated_image():
    """Return the annotated image as bytes"""
    try:
        fig, ax = plt.subplots()
        ax.imshow(st.session_state.active_image)
        ax.axis('off')

        # Redraw all annotations
        for drawing in st.session_state.drawings:
            if drawing['type'] == 'line':
                line = plt.Line2D(
                    [drawing['x0'], drawing['x1']],
                    [drawing['y0'], drawing['y1']],
                    color=drawing['color'],
                    linewidth=drawing['width']
                )
                ax.add_line(line)

        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, dpi=300)
        buf.seek(0)
        plt.close(fig)
        return buf
    except Exception as e:
        st.error(f"Error generating annotated image: {str(e)}")
        return None


def reset_session_state():
    """Reset the session state"""
    st.session_state.drawings = []
    st.session_state.current_tool = "select"
    st.session_state.bg_removed_image = None
    st.session_state.original_image = None
    st.session_state.active_image = None
    st.session_state.start_point = None
    st.session_state.fig = None


if __name__ == "__main__":
    # Install rembg if not available
    try:
        from rembg import remove
    except ImportError:
        st.warning("Installing background removal dependencies...")
        os.system("pip install rembg")
        from rembg import remove

    main()
