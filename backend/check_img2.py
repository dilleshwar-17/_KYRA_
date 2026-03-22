from PIL import Image

img_path = r'C:\Users\srira\OneDrive\Desktop\MINI_Project_folders\jarvis\frontend\public\kyra_front.png'
try:
    with Image.open(img_path) as img:
        w, h = img.size
        print(f"Image shape: {w}x{h}")
        pixels = img.load()
        
        # Look specifically in the 30% to 50% height range
        left_xs = []
        left_ys = []
        right_xs = []
        right_ys = []
        
        for y in range(int(h * 0.25), int(h * 0.55)):
            for x in range(w):
                # find dark pixels
                p = pixels[x, y]
                r, g, b, a = p if len(p) == 4 else (*p, 255)
                if a > 50 and (r+g+b)/3 < 70:
                    if x < w/2:
                        left_xs.append(x)
                        left_ys.append(y)
                    else:
                        right_xs.append(x)
                        right_ys.append(y)
        
        if left_xs and right_xs:
            avg_lx = sum(left_xs) / len(left_xs)
            avg_ly = sum(left_ys) / len(left_ys)
            avg_rx = sum(right_xs) / len(right_xs)
            avg_ry = sum(right_ys) / len(right_ys)
            
            print("--- RESULTS ---")
            print(f"Left Eye: X={avg_lx/w:.3f}%  Y={avg_ly/h:.3f}%")
            print(f"Right Eye: X={avg_rx/w:.3f}%  Y={avg_ry/h:.3f}%")
            print(f"Current TSX settings: Left X=0.32, Right X=0.58, Y=0.20")
except Exception as e:
    print("Error:", e)
