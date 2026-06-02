import curses
import numpy as np
import sounddevice as sd
import threading
import time
import re
import math

SAMPLE_RATE = 44100
BUFFER_SIZE = 1024
T_STEP = 8000  # t advances at original 8000 Hz rate
T_DEN = 44100

OPERATORS = ['&', '|', '^', '+', '-', '/', '*', '%', '<<', '>>']
HEX_CHARS = '0123456789abcdef'

buf = "t"
cursor = 1
undo_stack = []
buffer_lock = threading.Lock()

t_frac = 0
t_current = 0
last_out = 0
hist = np.zeros(256, dtype=np.uint8)
log_t = []
log_o = []
telemetry_lock = threading.Lock()

save_message = ""
save_message_time = 0

signed_mode = False

def save_to_undo():
    global buf, undo_stack
    if len(undo_stack) > 50:
        undo_stack.pop(0)
    undo_stack.append(buf)

def eval_rpn(str_expr, t):
    clean_str = str_expr.replace(',', ' ')
    tokens = [tok for tok in re.split(r'(<<|>>|[\s\&\|\^\+\-\/\*\%t\,])', clean_str) if tok.strip()]
    
    stack = []
    for token in tokens:
        if token == 't':
            stack.append(t & 0xFFFFFFFF)
        elif token in OPERATORS:
            if len(stack) < 2: return 0
            b = stack.pop()
            a = stack.pop()
            try:
                if token == '&': res = a & b
                elif token == '|': res = a | b
                elif token == '^': res = a ^ b
                elif token == '+': res = (a + b) & 0xFFFFFFFF
                elif token == '-': res = (a - b) & 0xFFFFFFFF
                elif token == '*':
                    res = (a * b) & 0xFFFFFFFF
                    if signed_mode and res >= 0x80000000:
                        res -= 0x100000000
                elif token == '/': res = (a // b) & 0xFFFFFFFF if b != 0 else 0
                elif token == '%':
                    if signed_mode:
                        res = int(math.fmod(a, b)) & 0xFFFFFFFF if b != 0 else 0
                    else:
                        res = (a % b) & 0xFFFFFFFF if b != 0 else 0
                elif token == '<<': res = (a << (b % 32)) & 0xFFFFFFFF
                elif token == '>>': res = (a >> (b % 32)) & 0xFFFFFFFF
                stack.append(res)
            except:
                stack.append(0)
        else:
            try:
                val = int(token, 16) & 0xFFFFFFFF
                stack.append(val)
            except ValueError:
                pass
                
    return (stack[-1] & 0xFF) if stack else 0

def audio_callback(outdata, frames, time_info, status):
    global buf, t_frac, t_current, last_out, hist, log_t, log_o
    with buffer_lock:
        local_buffer = buf
        
    out_samples = np.zeros(frames, dtype=np.uint8)
    lt = t_frac
    ct = t_current
    
    for i in range(frames):
        out_samples[i] = eval_rpn(local_buffer, ct)
        hist[ct % 256] = out_samples[i]
        lt += T_STEP
        if lt >= T_DEN:
            lt -= T_DEN
            ct += 1
            
    t_frac = lt
    t_current = ct
    
    with telemetry_lock:
        last_out = out_samples[-1] if frames > 0 else 0
        
        log_t.insert(0, f"t:0x{t_current:08X}")
        if len(log_t) > 10: log_t.pop()
            
        log_o.insert(0, f"OUT:0x{last_out:02X}")
        if len(log_o) > 10: log_o.pop()

    outdata[:, 0] = (out_samples / 127.5) - 1.0

def get_operator_at(s, idx):
    if idx < len(s) - 1 and s[idx:idx+2] in ['<<', '>>']: return s[idx:idx+2], idx, 2
    if idx > 0 and s[idx-1:idx+1] in ['<<', '>>']: return s[idx-1:idx+1], idx-1, 2
    if idx < len(s) and s[idx] in OPERATORS: return s[idx], idx, 1
    return None, idx, 0

def fuzzfind(stdscr):
    try:
        with open("bytebeat_presets.txt", "r") as f:
            presets = [line.rstrip('\n') for line in f if line.strip()]
    except FileNotFoundError:
        return None
    if not presets:
        return None
    stdscr.nodelay(False)
    query = ""
    selected = 0
    scroll = 0
    filtered = list(presets)
    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        stdscr.addstr(0, 0, f": {query}")
        max_items = max_y - 2
        if selected < scroll:
            scroll = selected
        if scroll + max_items > len(filtered):
            scroll = max(0, len(filtered) - max_items)
        if selected >= scroll + max_items:
            scroll = selected - max_items + 1
        if scroll < 0:
            scroll = 0
        vis = filtered[scroll:scroll + max_items]
        for i, item in enumerate(vis):
            style = curses.A_REVERSE if i == selected - scroll else curses.A_NORMAL
            display = item[:max_x - 1] if len(item) >= max_x else item
            try:
                stdscr.addstr(1 + i, 0, display, style)
            except:
                pass
        stdscr.refresh()
        ch = stdscr.getch()
        if ch == 27:
            stdscr.nodelay(True)
            return None
        elif ch in (10, 13):
            stdscr.nodelay(True)
            return filtered[selected] if filtered else None
        elif ch in (curses.KEY_BACKSPACE, 127, 8, 263):
            query = query[:-1]
        elif ch == curses.KEY_UP:
            selected = max(0, selected - 1)
        elif ch == curses.KEY_DOWN:
            selected = min(len(filtered) - 1, selected + 1)
        elif 32 <= ch <= 126:
            query += chr(ch)
        filtered = [p for p in presets if query.lower() in p.lower()]
        if filtered:
            selected = min(selected, len(filtered) - 1)
        else:
            selected = 0

def show_help(stdscr):
    try:
        with open("help.txt", "r") as f:
            lines = [line.rstrip('\n') for line in f]
    except FileNotFoundError:
        return
    if not lines:
        return
    stdscr.nodelay(False)
    scroll = 0
    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        max_items = max_y - 1
        if scroll + max_items > len(lines):
            scroll = max(0, len(lines) - max_items)
        if scroll < 0:
            scroll = 0
        for i, line in enumerate(lines[scroll:scroll + max_items]):
            display = line[:max_x - 1] if len(line) >= max_x else line
            try:
                stdscr.addstr(i, 0, display)
            except:
                pass
        if len(lines) > max_items:
            try:
                stdscr.addstr(max_y - 1, 0, "-- more ↑/↓ --" if scroll + max_items < len(lines) else "-- end --")
            except:
                pass
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (27, ord('q'), ord('Q')):
            break
        elif ch in (10, 13, 32):
            break
        elif ch == curses.KEY_UP:
            scroll = max(0, scroll - 1)
        elif ch == curses.KEY_DOWN:
            scroll = min(len(lines) - 1, scroll + 1)
    stdscr.nodelay(True)

def main(stdscr):
    global buf, cursor, undo_stack, log_t, log_o, hist, save_message, save_message_time, t_current, t_frac, signed_mode
    curses.curs_set(0)
    curses.use_default_colors()
    stdscr.nodelay(True)
    stdscr.clear()
    
    stream = sd.OutputStream(channels=1, callback=audio_callback, samplerate=SAMPLE_RATE, blocksize=BUFFER_SIZE)
    stream.start()
    
    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        
        if signed_mode:
            stdscr.addstr(0, 0, "SIGNED", curses.A_BOLD)

        y_pos, x_offset = 1, 2
        with buffer_lock:
            tokens = re.split(r'(<<|>>|[\s\&\|\^\+\-\/\*\%t\,])', buf)
            current_x = x_offset
            char_count = 0
            
            for token in tokens:
                if not token: continue
                for char in token:
                    is_cursor = (char_count == cursor)
                    style = curses.A_BOLD if (token in OPERATORS or token == 't') else curses.A_NORMAL
                    
                    if is_cursor:
                        stdscr.addstr(y_pos, current_x, char, style | curses.A_REVERSE)
                    else:
                        stdscr.addstr(y_pos, current_x, char, style)
                    
                    current_x += 1
                    char_count += 1
                    
            if cursor >= len(buf):
                stdscr.addstr(y_pos, current_x, " ", curses.A_REVERSE)
                
        with telemetry_lock:
            local_log_t = list(log_t)
            local_log_o = list(log_o)
            
        stdscr.addstr(3, 2, "--------------------------------------------------------", curses.A_DIM)
        for i in range(min(10, len(local_log_t))):
            style = curses.A_BOLD if i == 0 else curses.A_DIM
            if i < len(local_log_t):
                stdscr.addstr(4 + i, 2, local_log_t[i], style)
            if i < len(local_log_o):
                stdscr.addstr(4 + i, 25, local_log_o[i], style)
                
        if save_message and (time.time() - save_message_time < 2):
            stdscr.addstr(14, 2, save_message, curses.A_BOLD)
        else:
            save_message = ""

        start_scope_y = 16
        scope_height = max_y - start_scope_y - 1
        scope_width = 64
        
        if scope_height > 3:
            refs = [(255, "0xFF"), (128, "0x80"), (0, "0x00")]
            for val, txt in refs:
                y_offset = int((1.0 - (val / 255.0)) * (scope_height - 1))
                stdscr.addstr(start_y := (start_scope_y + y_offset), 2, f"{txt} +", curses.A_DIM)
                stdscr.addstr(start_y, 9, "-" * scope_width, curses.A_DIM)
            
            for xs in range(scope_width):
                val = hist[(xs * 4) % 256]
                y_offset = int((1.0 - (val / 255.0)) * (scope_height - 1))
                stdscr.addstr(start_scope_y + y_offset, 9 + xs, "*")

        stdscr.refresh()
        
        try:
            ch = stdscr.getkey()
        except:
            time.sleep(0.015)
            continue
            
        if ch == 'q':
            break
        if ch == 'r':
            t_current = 0
            t_frac = 0
        if ch == 's':
            signed_mode = not signed_mode
        if ch == '?':
            show_help(stdscr)
        if ch == ':':
            result = fuzzfind(stdscr)
            if result is not None:
                with buffer_lock:
                    save_to_undo()
                    buf = result
                    cursor = len(buf)

        with buffer_lock:
            if ch == 'h':
                cursor = max(0, cursor - 1)
            elif ch == 'l':
                cursor = min(len(buf), cursor + 1)
            elif ch == '$':
                if cursor >= len(buf):
                    cursor = 0
                else:
                    cursor = len(buf)
            elif ch == 'u' and undo_stack:
                buf = undo_stack.pop()
                cursor = min(cursor, len(buf))
            elif ch == 'w':
                try:
                    with open("bytebeat_presets.txt", "a", encoding="utf-8") as f:
                        f.write(buf + "\n")
                    save_message = "[ Guardado en bytebeat_presets.txt ]"
                except Exception as e:
                    save_message = f"[ Error al guardar: {str(e)} ]"
                save_message_time = time.time()
            elif ch in ('KEY_BACKSPACE', '\b', '\x7f'):
                if cursor > 0:
                    save_to_undo()
                    if cursor >= 2 and buf[cursor-2:cursor] in ('<<', '>>'):
                        buf = buf[:cursor-2] + buf[cursor:]
                        cursor -= 2
                    else:
                        buf = buf[:cursor-1] + buf[cursor:]
                        cursor -= 1
            elif ch == 'x' and buf:
                save_to_undo()
                op, op_start, op_len = get_operator_at(buf, cursor)
                if op:
                    buf = buf[:op_start] + buf[op_start+op_len:]
                    cursor = min(op_start, len(buf))
                else:
                    if cursor < len(buf):
                        buf = buf[:cursor] + buf[cursor+1:]
                    if cursor >= len(buf) and cursor > 0:
                        cursor = len(buf)
            elif ch in ['j', 'k'] and buf:
                if cursor < len(buf):
                    save_to_undo()
                    dir_val = 1 if ch == 'k' else -1
                    op, op_start, op_len = get_operator_at(buf, cursor)
                    if op:
                        idx = OPERATORS.index(op)
                        new_op = OPERATORS[(idx + dir_val) % len(OPERATORS)]
                        buf = buf[:op_start] + new_op + buf[op_start+op_len:]
                        cursor = op_start
                    elif buf[cursor].lower() in HEX_CHARS:
                        idx = HEX_CHARS.index(buf[cursor].lower())
                        buf = buf[:cursor] + HEX_CHARS[(idx + dir_val) % 16] + buf[cursor+1:]
            elif ch in ['<', '>']:
                save_to_undo()
                ins = "<<" if ch == '<' else ">>"
                buf = buf[:cursor] + ins + buf[cursor:]
                cursor += 2
            elif len(ch) == 1:
                u_ch = ch.lower()
                if u_ch not in ['w', 'u'] and (u_ch in HEX_CHARS or ch in ['t', ' ', ','] or ch in OPERATORS):
                    save_to_undo()
                    buf = buf[:cursor] + ch + buf[cursor:]
                    cursor += 1

    stream.stop()

if __name__ == '__main__':
    curses.wrapper(main)
