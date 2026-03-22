from PIL import Image

img_path = r'C:\Users\srira\OneDrive\Desktop\MINI_Project_folders\jarvis\frontend\public\kyra_front.png'
try:
    with Image.open(img_path) as img:
        w, h = img.size
        pixels = img.load()
        
        # Print a small ascii map of the image to see where the head actually is
        # We'll sample a 20x20 grid
        print("ASCII Map of Avatar (Width/Height)")
        for y in range(0, h, h//30):
            row_str = ""
            for x in range(0, w, w//20):
                p = pixels[x, y]
                r, g, b, a = p if len(p) == 4 else (*p, 255)
                if a < 50:
                    row_str += " . "
                elif (r+g+b)/3 < 60:
                    row_str += " # " # Dark (hair, eyes, clothes)
                elif r > g and r > b and g > b:
                    row_str += " = " # Skin/warm
                else:
                    row_str += " O " # Other
            print(f"{y/h:.2f} | {row_str}")
            
except Exception as e:
    print(e)
