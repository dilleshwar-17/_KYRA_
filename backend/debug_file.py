import os

def debug_file():
    path = r"C:\Users\srira\OneDrive\Desktop\MINI_Project_folders\jarvis\backend\.env"
    print(f"Path: {path}")
    if os.path.isfile(path):
        with open(path, "r") as f:
            content = f.read()
            print(f"Content: {repr(content)}")
            for line in content.splitlines():
                print(f"Line: {repr(line)}")
    else:
        print("File not found")

if __name__ == "__main__":
    debug_file()
