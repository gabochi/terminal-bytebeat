import curses

def draw_interface(stdscr, engine, t_idx, c_idx):
    stdscr.erase()
    
    # Dibujar Tokens con cursor en REVERSE puro
    curr_x = 2
    cursor_pos_x = 2
    for i, token in enumerate(engine.tokens):
        for char_pos, char in enumerate(token):
            if i == t_idx and char_pos == c_idx:
                attr = curses.A_REVERSE  # Solo reverse para máxima claridad
                cursor_pos_x = curr_x
            else:
                attr = curses.A_NORMAL
            
            stdscr.addstr(1, curr_x, char, attr)
            curr_x += 1
        curr_x += 1 # Espacio entre tokens
    
    # Cascada de valores
    for i, (ct, cv) in enumerate(engine.cascade):
        attr = curses.A_BOLD if i == 0 else curses.A_DIM
        try:
            stdscr.addstr(4 + i, 2, f"{ct:08X} {cv:02X}", attr)
        except: pass

    # Osciloscopio
    scope_x_start, scope_height = 15, 12
    for x, val_255 in enumerate(engine.last_samples):
        y_pos = (scope_height - 1) - int((val_255 / 255.0) * (scope_height - 1))
        try:
            stdscr.addch(4 + y_pos, scope_x_start + x, "█")
        except: pass

    if engine.paused:
        stdscr.addstr(0, 2, "[!]", curses.A_BOLD)
    
    # El cursor físico de la terminal se queda donde está el reverse
    stdscr.move(1, cursor_pos_x)
    stdscr.refresh()
