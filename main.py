import curses
import sounddevice as sd
import copy
from constants import SAMPLE_RATE
from engine import RPNEngine
from ui import draw_interface
from input_handler import handle_key

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    
    engine = RPNEngine()
    t_idx, c_idx = 0, 0

    with sd.OutputStream(channels=1, samplerate=SAMPLE_RATE, callback=engine.callback):
        running = True
        while running:
            # 1. Lógica de Audio
            if not engine.paused:
                engine.active_tokens = copy.deepcopy(engine.tokens)
            
            # 2. Lógica de UI
            draw_interface(stdscr, engine, t_idx, c_idx)
            engine.cascade.appendleft((engine.t, engine.last_val))

            # 3. Lógica de Input
            try:
                key = stdscr.getkey()
            except:
                key = ""
            
            t_idx, c_idx, running = handle_key(key, engine, t_idx, c_idx)

if __name__ == "__main__":
    curses.wrapper(main)
