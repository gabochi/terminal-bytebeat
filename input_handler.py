import string
from constants import OPERATORS, OP_MAP, SAVE_FILE, HEX_CHARS

def handle_key(key, engine, t_idx, c_idx):
    if not key: return t_idx, c_idx, True
    if key == 'q': return t_idx, c_idx, False

    # Atajos de navegación de palabras (Tokens)
    if key == '$':
        t_idx = len(engine.tokens) - 1
        c_idx = len(engine.tokens[t_idx]) - 1
    
    elif key == 'W': # Siguiente término
        if t_idx < len(engine.tokens) - 1:
            t_idx += 1
            c_idx = 0
            
    elif key == 'E': # Final del término actual o siguiente
        if c_idx == len(engine.tokens[t_idx]) - 1:
            if t_idx < len(engine.tokens) - 1:
                t_idx += 1
        c_idx = len(engine.tokens[t_idx]) - 1
        
    elif key == 'B': # Inicio del término
        if c_idx == 0 and t_idx > 0:
            t_idx -= 1
        c_idx = 0

    # Movimiento carácter a carácter
    elif key in ['KEY_LEFT', 'h']:
        if c_idx > 0: c_idx -= 1
        elif t_idx > 0:
            t_idx -= 1
            c_idx = len(engine.tokens[t_idx]) - 1
            
    elif key in ['KEY_RIGHT', 'l']:
        if c_idx < len(engine.tokens[t_idx]) - 1: c_idx += 1
        elif t_idx < len(engine.tokens) - 1:
            t_idx += 1
            c_idx = 0

    # Modificación de valores
    elif key in ['KEY_UP', 'k', 'KEY_DOWN', 'j']:
        engine.save_state()
        token = engine.tokens[t_idx]
        delta = 1 if key in ['KEY_UP', 'k'] else -1
        if token in OPERATORS:
            idx = OPERATORS.index(token)
            engine.tokens[t_idx] = OPERATORS[(idx + delta) % len(OPERATORS)]
            c_idx = 0
        else:
            v_h = HEX_CHARS.find(token[c_idx].upper())
            n_c = HEX_CHARS[(v_h + delta) % 16]
            l_t = list(token)
            l_t[c_idx] = n_c
            engine.tokens[t_idx] = "".join(l_t)

    # Estado y archivos
    elif key == '!': engine.paused = not engine.paused
    elif key == 'u':
        engine.undo()
        t_idx = min(t_idx, len(engine.tokens) - 1)
        c_idx = 0
    elif key == 'w':
        with open(SAVE_FILE, "a") as f:
            f.write(" ".join(engine.tokens) + "\n")
    elif key == 'i':
        engine.save_state()
        engine.tokens.insert(t_idx + 1, "000")
        t_idx += 1
        c_idx = 2
    elif key == 'A':
        engine.save_state()
        engine.tokens.insert(len(engine.tokens) + 1, "000")
        t_idx = len(engine.tokens) - 1
        c_idx = 2
    elif key == 'x':
        if len(engine.tokens) > 1:
            engine.save_state()
            engine.tokens.pop(t_idx)
            t_idx = max(0, t_idx - 1)
            c_idx = 0

    # Inserción de operadores o números HEX
    elif key in OP_MAP:
        engine.save_state()
        engine.tokens[t_idx] = OP_MAP[key]
        c_idx = 0
    elif all(c in string.hexdigits.lower() for c in key):
        engine.save_state()
        if engine.tokens[t_idx] in OPERATORS:
            engine.tokens[t_idx] = key.upper().zfill(4)
            c_idx = 0
        else:
            l_t = list(engine.tokens[t_idx])
            l_t[c_idx] = key.upper()
            engine.tokens[t_idx] = "".join(l_t)

    return t_idx, c_idx, True

