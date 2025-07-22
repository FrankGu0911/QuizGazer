import mss
import mss.tools
import os,time
from PIL import Image
import io
from utils.config_manager import get_app_config

def get_available_screens():
    """
    Gets information about all available screens.
    
    Returns:
        list: A list of dictionaries with screen information.
    """
    with mss.mss() as sct:
        screens = []
        for i, monitor in enumerate(sct.monitors):
            # Skip the "all monitors" entry which is at index 0
            if i == 0:
                continue
                
            screens.append({
                'number': i,
                'width': monitor['width'],
                'height': monitor['height'],
                'left': monitor['left'],
                'top': monitor['top']
            })
        return screens

def take_screenshot():
    """
    Takes a screenshot of the selected monitor and resizes it if it's too large.

    Returns:
        bytes: The screenshot image data in PNG format as bytes.
    """
    # Get screen number from config
    app_config = get_app_config()
    screen_number = app_config.get('screen_number', 1)
    
    with mss.mss() as sct:
        # Ensure screen number is valid
        if screen_number < 1 or screen_number >= len(sct.monitors):
            print(f"Invalid screen number {screen_number}, defaulting to 1")
            screen_number = 1
            
        # Get information of the selected monitor
        mon = sct.monitors[screen_number]

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
        if not os.path.exists("screenshot"):
            os.makedirs("screenshot")
        cur_time=time.strftime("%Y-%m-%d_%H-%M-%S")
        screen_path = f"./screenshot/{cur_time}.png"
        with open(screen_path, "wb") as f:
            img.save(f,format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        return img_byte_arr