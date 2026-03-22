from PIL import Image

img_path = r'C:\Users\srira\OneDrive\Desktop\MINI_Project_folders\jarvis\frontend\public\kyra_front.png'
try:
    with Image.open(img_path) as img:
        w, h = img.size
        print(f"Image shape: {w}x{h}")
        # Let's inspect a horizontal line at 20% height to find dark pixels (the eyes)
        y = int(h * 0.20)
        print(f"Blink Y-level: {y}")
        # Find where the dark pixels are
        pixels = img.load()
        dark_xs = []
        for x in range(w):
            r, g, b, a = pixels[x, y] if len(pixels[x,y]) == 4 else (*pixels[x,y], 255)
            if a > 0 and (r+g+b)/3 < 100: # Relatively dark
                dark_xs.append(x)
        
        if dark_xs:
            print(f"Dark pixels at 20% height exist between x={min(dark_xs)} and x={max(dark_xs)}.")
            # Let's check 25%, 30%, 35% height to see where the real eyes are
            for pct in [0.25, 0.30, 0.35, 0.40, 0.45]:
                py = int(h * pct)
                row_dark = []
                for x in range(w):
                    r, g, b, a = pixels[x, py] if len(pixels[x,py]) == 4 else (*pixels[x,py], 255)
                    if a > 0 and (r+g+b)/3 < 80:
                        row_dark.append(x)
                if len(row_dark) > 10:
                    left_eye_center = sum([x for x in row_dark if x < w/2]) / max(len([x for x in row_dark if x < w/2]), 1)
                    right_eye_center = sum([x for x in row_dark if x > w/2]) / max(len([x for x in row_dark if x > w/2]), 1)
                    print(f"At {int(pct*100)}% height: Possible eyes at X={left_eye_center:.1f} ({left_eye_center/w:.2f}) and X={right_eye_center:.1f} ({right_eye_center/w:.2f})")
except Exception as e:
    print("Error:", e)
