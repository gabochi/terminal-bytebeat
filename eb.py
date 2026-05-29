import curses
import numpy as np
import sounddevice as sd
import threading
import time
import re

SAMPLE_RATE = 8000
BUFFER_SIZE = 1024

OPERATORS = ['&', '|', '^', '+', '-', '/', '*', '%', '<<', '>>']
HEX_CHARS = '0123456789ABCDEF'

buf = "t"
cursor = 1
undo_stack = []
buffer_lock = threading.Lock()

# Estados globales de audio, osciloscopio y cascadas (logs)
global_t = 0
last_out = 0
hist = np.zeros(256, dtype=np.uint8)
log_t = []
log_o = []
telemetry_lock = threading.Lock()

# Estado de mensaje de guardado
save_message = ""
save_message_time = 0

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
                elif token == '*': res = (a * b) & 0xFFFFFFFF
                elif token == '/': res = (a // b) & 0xFFFFFFFF if b != 0 else 0
                elif token == '%': res = (a % b) & 0xFFFFFFFF if b != 0 else 0
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
    global buf, global_t, last_out, hist, log_t, log_o
    with buffer_lock:
        local_buffer = buf
        
    out_samples = np.zeros(frames, dtype=np.uint8)
    current_t = global_t
    
    for i in range(frames):
        out_samples[i] = eval_rpn(local_buffer, current_t)
        hist[current_t % 256] = out_samples[i]
        current_t += 1
        
    global_t = current_t
    
    with telemetry_lock:
        last_out = out_samples[-1] if frames > 0 else 0
        
        log_t.insert(0, f"t:0x{global_t:08X}")
        if len(log_t) > 10: log_t.pop()
            
        log_o.insert(0, f"OUT:0x{last_out:02X}")
        if len(log_o) > 10: log_o.pop()

    outdata[:, 0] = (out_samples / 127.5) - 1.0

def get_operator_at(s, idx):
    if idx < len(s) - 1 and s[idx:idx+2] in ['<<', '>>']: return s[idx:idx+2], idx, 2
    if idx > 0 and s[idx-1:idx+1] in ['<<', '>>']: return s[idx-1:idx+1], idx-1, 2
    if idx < len(s) and s[idx] in OPERATORS: return s[idx], idx, 1
    return None, idx, 0

def main(stdscr):
    global buf, cursor, undo_stack, log_t, log_o, hist, save_message, save_message_time
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.clear()
    
    stream = sd.OutputStream(channels=1, callback=audio_callback, samplerate=SAMPLE_RATE, blocksize=BUFFER_SIZE)
    stream.start()
    
    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        
        # 1. Expresión RPN
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
                
        # 2. Cascada de Texto Ampliada (10 líneas)
        with telemetry_lock:
            local_log_t = list(log_t)
            local_log_o = list(log_o)
            
        stdscr.addstr(3, 2, "────────────────────────────────────────────────────────", curses.A_DIM)
        for i in range(min(10, len(local_log_t))):
            style = curses.A_BOLD if i == 0 else curses.A_DIM
            if i < len(local_log_t):
                stdscr.addstr(4 + i, 2, local_log_t[i], style)
            if i < len(local_log_o):
                stdscr.addstr(4 + i, 25, local_log_o[i], style)
                
        # Mostrar notificación de guardado temporal debajo de la cascada
        if save_message and (time.time() - save_message_time < 2):
            stdscr.addstr(14, 2, save_message, curses.A_BOLD)
        else:
            save_message = ""

        # 3. Osciloscopio más compacto
        start_scope_y = 16
        scope_height = max_y - start_scope_y - 1
        scope_width = 64
        
        if scope_height > 3:
            refs = [(255, "0xFF"), (128, "0x80"), (0, "0x00")]
            for val, txt in refs:
                y_offset = int((1.0 - (val / 255.0)) * (scope_height - 1))
                stdscr.addstr(start_y := (start_scope_y + y_offset), 2, f"{txt} ┼", curses.A_DIM)
                stdscr.addstr(start_y, 9, "─" * scope_width, curses.A_DIM)
            
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
            
        with buffer_lock:
            if ch == 'h':
                cursor = max(0, cursor - 1)
            elif ch == 'l':
                cursor = min(len(buf), cursor + 1)
            elif ch == 'u' and undo_stack:
                buf = undo_stack.pop()
                cursor = min(cursor, len(buf))
            elif ch == 'w':
                # Guardar expresión actual en un archivo de texto plano
                try:
                    with open("bytebeat_presets.txt", "a", encoding="utf-8") as f:
                        f.write(buf + "\n")
                    save_message = "[ Guardado en bytebeat_presets.txt ]"
                except Exception as e:
                    save_message = f"[ Error al guardar: {str(e)} ]"
                save_message_time = time.time()
            elif ch == 'x' and buf:
                save_to_undo()
                op, op_start, op_len = get_operator_at(buf, cursor)
                if op:
                    buf = buf[:op_start] + buf[op_start+op_len:]
                    cursor = max(0, op_start - 1)
                else:
                    if cursor < len(buf):
                        buf = buf[:cursor] + buf[cursor+1:]
                    if cursor >= len(buf) and cursor > 0:
                        cursor = len(buf) - 1
            elif ch in ['j', 'k'] and buf:
                # Evitar mutaciones si el cursor está al final en el espacio vacío
                if cursor < len(buf):
                    save_to_undo()
                    dir_val = 1 if ch == 'k' else -1
                    op, op_start, op_len = get_operator_at(buf, cursor)
                    if op:
                        idx = OPERATORS.index(op)
                        new_op = OPERATORS[(idx + dir_val) % len(OPERATORS)]
                        buf = buf[:op_start] + new_op + buf[op_start+op_len:]
                        cursor = op_start
                    elif buf[cursor].upper() in HEX_CHARS:
                        idx = HEX_CHARS.index(buf[cursor].upper())
                        buf = buf[:cursor] + HEX_CHARS[(idx + dir_val) % 16] + buf[cursor+1:]
            elif ch in ['<', '>']:
                save_to_undo()
                ins = "<<" if ch == '<' else ">>"
                buf = buf[:cursor] + ins + buf[cursor:]
                cursor += 2
            elif len(ch) == 1:
                u_ch = ch.upper()
                # Excluir 'w' y 'u' de la inserción directa para preservar sus atajos de control
                if u_ch not in ['W', 'U'] and (u_ch in HEX_CHARS or ch in ['t', ' ', ','] or ch in OPERATORS):
                    save_to_undo()
                    buf = buf[:cursor] + ch + buf[cursor:]
                    cursor += 1

    stream.stop()

if __name__ == '__main__':
    curses.wrapper(main)

