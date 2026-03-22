from PIL import Image, ImageDraw

img_path = r'C:\Users\srira\OneDrive\Desktop\MINI_Project_folders\jarvis\frontend\public\kyra_front.png'
out_path = r'C:\Users\srira\OneDrive\Desktop\MINI_Project_folders\jarvis\backend\debug_avatar.png'

try:
    with Image.open(img_path) as img:
        img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        
        # Draw the existing TSX points
        # Left eye: 0.32, 0.20
        # Right eye: 0.58, 0.20
        # Mouth: 0.44, 0.285
        
        ex_l = w * 0.32
        ex_r = w * 0.58
        ey = h * 0.20
        mouth_x = w * 0.44
        mouth_y = h * 0.285
        
        draw.ellipse([ex_l-5, ey-5, ex_l+5, ey+5], fill="red")
        draw.ellipse([ex_r-5, ey-5, ex_r+5, ey+5], fill="blue")
        draw.ellipse([mouth_x-5, mouth_y-5, mouth_x+5, mouth_y+5], fill="green")
        
        # Let's also draw the script's detected points
        draw.ellipse([w*0.349-5, h*0.392-5, w*0.349+5, h*0.392+5], fill="purple")
        draw.ellipse([w*0.693-5, h*0.406-5, w*0.693+5, h*0.406+5], fill="purple")
        
        img.save(out_path)
        print("Debug image saved.")
except Exception as e:
    print(e)
