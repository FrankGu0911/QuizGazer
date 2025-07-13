import mss
import mss.tools
from PIL import Image
import io

def take_screenshot():
    """
    Takes a screenshot of the primary monitor and resizes it if it's too large.

    Returns:
        bytes: The screenshot image data in PNG format as bytes.
    """
    with mss.mss() as sct:
        # Get information of monitor 1
        monitor_number = 1
        mon = sct.monitors[monitor_number]

        # Grab the data
        sct_img = sct.grab(mon)

        # Convert to a PIL Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        # --- Resize logic ---
        MAX_DIMENSION = 1920  # Corresponds to 1080p's longer side
        width, height = img.size
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            if width > height:
                new_width = MAX_DIMENSION
                new_height = int(height * (MAX_DIMENSION / width))
            else:
                new_height = MAX_DIMENSION
                new_width = int(width * (MAX_DIMENSION / height))
            
            print(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
            # Use Resampling.LANCZOS for newer Pillow versions, fall back to LANCZOS
            resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
            img = img.resize((new_width, new_height), resample_filter)
        # --- End of resize logic ---
        
        # Save the image to a bytes buffer
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        return img_byte_arr