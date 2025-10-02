import re
from datetime import datetime

def generate_meta_description(text: str, max_len=160):
    clean = re.sub(r'<[^>]*>', '', text)
    clean = clean.replace('\n', ' ').strip()
    return clean[:max_len].strip() + ("..." if len(clean) > max_len else "")

def format_rfc2822(dt_str):
    if isinstance(dt_str, str):
        dt = datetime.strptime(dt_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
    else:
        dt = dt_str
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
