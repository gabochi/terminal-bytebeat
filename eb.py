#!/usr/bin/env python3
import argparse
import curses
import sounddevice as sd
import time

import editor
from engine import RPNEngine
from visuals import draw_expression, draw_cascade, PhasePortrait, BitPlanes, Waveform
from layout import LayoutManager, LAYOUTS


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
            except Exception:
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
        elif ch == curses.KEY_UP or ch == ord('k'):
            selected = max(0, selected - 1)
        elif ch == curses.KEY_DOWN or ch == ord('j'):
            selected = min(len(filtered) - 1, selected + 1)
        elif ch == ord('h'):
            selected = max(0, selected - max_items)
        elif ch == ord('l'):
            selected = min(len(filtered) - 1, selected + max_items)
        elif 32 <= ch <= 126 and chr(ch).lower() in editor.HEX_CHARS + 't, &|^+-*/%<>':
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
            except Exception:
                pass
        if len(lines) > max_items:
            try:
                stdscr.addstr(max_y - 1, 0,
                              "-- more \u2191/\u2193 --" if scroll + max_items < len(lines) else "-- end --")
            except Exception:
                pass
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (27, ord('q'), ord('Q')):
            break
        elif ch in (10, 13, 32):
            break
        elif ch == curses.KEY_UP or ch == ord('k'):
            scroll = max(0, scroll - 1)
        elif ch == curses.KEY_DOWN or ch == ord('j'):
            scroll = min(len(lines) - 1, scroll + 1)
        elif ch == ord('h'):
            scroll = max(0, scroll - max_items)
        elif ch == ord('l'):
            scroll = min(len(lines) - 1, scroll + max_items)
    stdscr.nodelay(True)


def main(stdscr, sample_rate=8000, t_step=1, t_den=1):
    curses.curs_set(0)
    curses.use_default_colors()
    stdscr.nodelay(True)
    stdscr.clear()

    engine = RPNEngine(sample_rate=sample_rate, t_step=t_step, t_den=t_den)
    phase = PhasePortrait(width=40)
    bits = BitPlanes(width=48)
    scope = Waveform(width=64)
    layout = LayoutManager(LAYOUTS[0])
    layout_idx = 0

    with sd.OutputStream(channels=1, callback=engine.callback,
                         samplerate=engine.SAMPLE_RATE,
                         blocksize=engine.BUFFER_SIZE):
        while True:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()

            with editor.buffer_lock:
                local_buf = editor.buf
                local_cursor = editor.cursor

            with engine.telemetry_lock:
                local_log_t = list(engine.log_t)
                local_log_o = list(engine.log_o)

            samples = list(engine.samples)

            draw_expression(stdscr, local_buf, local_cursor,
                            engine.signed_mode, y=layout.y('expr'))
            draw_cascade(stdscr, local_log_t, local_log_o, y=layout.y('cascade'))

            sep_y = layout.y('cascade') + 1
            try:
                stdscr.addstr(sep_y, 0, "-" * max_x, curses.A_DIM)
            except Exception:
                pass

            bits.render(stdscr, 2, layout.y('bits'), samples,
                        height=layout.h('bits'))

            sep_y = layout.y('bits') + layout.h('bits')
            try:
                stdscr.addstr(sep_y, 0, "-" * max_x, curses.A_DIM)
            except Exception:
                pass

            phase.render(stdscr, 2, layout.y('phase'), samples,
                         height=layout.h('phase'))

            sep_y = layout.y('phase') + layout.h('phase')
            try:
                stdscr.addstr(sep_y, 0, "-" * max_x, curses.A_DIM)
            except Exception:
                pass

            min_val, peak = scope.render(stdscr, 2, layout.y('scope'), samples,
                                         height=layout.h('scope'))

            try:
                stdscr.addstr(layout.y('labels'), 0,
                              f"[{layout.name}] "
                              f"min:0x{min_val:02X}  peak:0x{peak:02X}",
                              curses.A_DIM)

            except Exception:
                pass

            if editor.save_message and (time.time() - editor.save_message_time < 2):
                try:
                    last_line = layout.y('labels')
                    stdscr.addstr(last_line, max_x - len(editor.save_message) - 2,
                                  editor.save_message, curses.A_BOLD)
                except Exception:
                    pass
            else:
                editor.save_message = ""

            stdscr.refresh()

            try:
                ch = stdscr.getkey()
            except Exception:
                time.sleep(0.015)
                continue

            if ch == 'q':
                break
            if ch == 'r':
                engine.reset()
            if ch == 's':
                engine.signed_mode = not engine.signed_mode
            if ch in ('\t', 'KEY_STAB'):
                layout_idx = (layout_idx + 1) % len(LAYOUTS)
                layout = LayoutManager(LAYOUTS[layout_idx])
            if ch == '?':
                show_help(stdscr)
            if ch == ':':
                result = fuzzfind(stdscr)
                if result is not None:
                    with editor.buffer_lock:
                        editor.save_to_undo()
                        editor.buf = result
                        editor.cursor = len(editor.buf)

            with editor.buffer_lock:
                if ch == 'h':
                    editor.cursor = max(0, editor.cursor - 1)
                elif ch == 'l':
                    editor.cursor = min(len(editor.buf), editor.cursor + 1)
                elif ch == '$':
                    if editor.cursor >= len(editor.buf):
                        editor.cursor = 0
                    else:
                        editor.cursor = len(editor.buf)
                elif ch == 'u' and editor.undo_stack:
                    editor.buf = editor.undo_stack.pop()
                    editor.cursor = min(editor.cursor, len(editor.buf))
                elif ch == 'w':
                    try:
                        with open("bytebeat_presets.txt", "a", encoding="utf-8") as f:
                            f.write(editor.buf + "\n")
                        editor.save_message = "[ Guardado en bytebeat_presets.txt ]"
                    except Exception as e:
                        editor.save_message = f"[ Error al guardar: {str(e)} ]"
                    editor.save_message_time = time.time()
                elif ch in ('KEY_BACKSPACE', '\b', '\x7f'):
                    if editor.cursor > 0:
                        editor.save_to_undo()
                        if editor.cursor >= 2 and editor.buf[editor.cursor-2:editor.cursor] in ('<<', '>>'):
                            editor.buf = editor.buf[:editor.cursor-2] + editor.buf[editor.cursor:]
                            editor.cursor -= 2
                        else:
                            editor.buf = editor.buf[:editor.cursor-1] + editor.buf[editor.cursor:]
                            editor.cursor -= 1
                elif ch == 'x' and editor.buf:
                    editor.save_to_undo()
                    op, op_start, op_len = editor.get_operator_at(editor.buf, editor.cursor)
                    if op:
                        editor.buf = editor.buf[:op_start] + editor.buf[op_start+op_len:]
                        editor.cursor = min(op_start, len(editor.buf))
                    else:
                        if editor.cursor < len(editor.buf):
                            editor.buf = editor.buf[:editor.cursor] + editor.buf[editor.cursor+1:]
                        if editor.cursor >= len(editor.buf) and editor.cursor > 0:
                            editor.cursor = len(editor.buf)
                elif ch in ['j', 'k'] and editor.buf:
                    if editor.cursor < len(editor.buf):
                        editor.save_to_undo()
                        dir_val = 1 if ch == 'k' else -1
                        op, op_start, op_len = editor.get_operator_at(editor.buf, editor.cursor)
                        if op:
                            idx = editor.OPERATORS.index(op)
                            new_op = editor.OPERATORS[(idx + dir_val) % len(editor.OPERATORS)]
                            editor.buf = editor.buf[:op_start] + new_op + editor.buf[op_start+op_len:]
                            editor.cursor = op_start
                        elif editor.buf[editor.cursor].lower() in editor.HEX_CHARS:
                            idx = editor.HEX_CHARS.index(editor.buf[editor.cursor].lower())
                            editor.buf = editor.buf[:editor.cursor] + editor.HEX_CHARS[(idx + dir_val) % 16] + editor.buf[editor.cursor+1:]
                elif ch in ['<', '>']:
                    editor.save_to_undo()
                    ins = "<<" if ch == '<' else ">>"
                    editor.buf = editor.buf[:editor.cursor] + ins + editor.buf[editor.cursor:]
                    editor.cursor += 2
                elif len(ch) == 1:
                    u_ch = ch.lower()
                    if u_ch not in ['w', 'u'] and (u_ch in editor.HEX_CHARS or ch in ['t', ' ', ','] or ch in editor.OPERATORS):
                        editor.save_to_undo()
                        editor.buf = editor.buf[:editor.cursor] + ch + editor.buf[editor.cursor:]
                        editor.cursor += 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='sbb bytebeat editor')
    parser.add_argument('--rate', type=int, default=8000,
                        help='Sample rate in Hz (default: 8000). '
                             'Rates > 8000 use fractional t-stepping.')
    args = parser.parse_args()

    if args.rate > 8000:
        kwargs = {'sample_rate': args.rate, 't_step': 8000, 't_den': args.rate}
    else:
        kwargs = {'sample_rate': 8000, 't_step': 1, 't_den': 1}

    curses.wrapper(lambda stdscr: main(stdscr, **kwargs))
