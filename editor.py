import threading

OPERATORS = ['&', '|', '^', '+', '-', '/', '*', '%', '<<', '>>']
HEX_CHARS = '0123456789abcdef'

buf = "t"
cursor = 1
undo_stack = []
buffer_lock = threading.Lock()

save_message = ""
save_message_time = 0


def save_to_undo():
    global buf, undo_stack
    if len(undo_stack) > 50:
        undo_stack.pop(0)
    undo_stack.append(buf)


def load_presets():
    try:
        with open("bytebeat_presets.txt", "r") as f:
            return [line.rstrip('\n') for line in f if line.strip()]
    except FileNotFoundError:
        return []


def get_operator_at(s, idx):
    if idx < len(s) - 1 and s[idx:idx+2] in ['<<', '>>']:
        return s[idx:idx+2], idx, 2
    if idx > 0 and s[idx-1:idx+1] in ['<<', '>>']:
        return s[idx-1:idx+1], idx-1, 2
    if idx < len(s) and s[idx] in OPERATORS:
        return s[idx], idx, 1
    return None, idx, 0
