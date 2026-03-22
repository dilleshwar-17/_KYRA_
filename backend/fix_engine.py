
import re

file_path = r'c:\Users\srira\OneDrive\Desktop\MINI_Project_folders\KYRA\backend\engine.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find the context line and the full_message line
pattern = r'(context = get_realtime_context\(\)\s+full_message = f")\{context\}\\n\[USER_EMOTION: \{emotion\}\] \[USER_SENTIMENT: \{sent_label\} \(\{sentiment:\.1f\}\)\] \{user_message\}"'
replacement = r'\1[SYSTEM_AWARENESS]\\n{context}\\nEmotion: {emotion}, Sentiment: {sent_label}\\n[/SYSTEM_AWARENESS]\\n\\n{user_message}"'

new_content = re.sub(pattern, replacement, content)

# Also ensure the system prompt rule is there (though I think I already added it)
if 'IMPORTANT: You are provided with a [REALTIME_CONTEXT] block' not in new_content:
    print("Warning: System prompt rule missing. Check logic.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Successfully updated engine.py")
