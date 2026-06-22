#!/usr/bin/env python3
import argparse
import random
import re
import time

import numpy as np
import pygame

import editor
from engine import RPNEngine

FFT_SIZE = 256
SPEC_HOP = 64


class SBBGui:
    def __init__(self, args):
        self.args = args
        self.show = {
            'waveform': not args.no_waveform,
            'phase': not args.no_phase,
            'bits': not args.no_bits,
            'spectrogram': not args.no_spectrogram,
        }

        if args.rate > 8000:
            engine_kwargs = {'sample_rate': args.rate, 't_step': 8000, 't_den': args.rate}
        else:
            engine_kwargs = {'sample_rate': 8000, 't_step': 1, 't_den': 1}

        self.engine = RPNEngine(**engine_kwargs)
        self.save_msg = ""
        self.save_msg_time = 0
        self.preset_idx = -1

        # Phase portrait state
        self.phase_grid = None
        self.phase_w = 0
        self.phase_h = 0

        # Spectrogram state
        self.spec_raw = []
        self.spec_next_fft = 0
        self.spec_cols = []

        pygame.init()
        self.WIDTH, self.HEIGHT = 800, 600
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("sbb \u2014 bytebeat")
        self.clock = pygame.time.Clock()
        self.running = True

        self.font = pygame.font.SysFont('monospace', 16)
        self.big_font = pygame.font.SysFont('monospace', 36)
        self.small_font = pygame.font.SysFont('monospace', 12)
        self.char_w = self.big_font.size('M')[0]

        self.calc_layout()

        import sounddevice as sd
        self.stream = sd.OutputStream(
            channels=1,
            callback=self.engine.callback,
            samplerate=self.engine.SAMPLE_RATE,
            blocksize=self.engine.BUFFER_SIZE,
        )
        self.stream.start()

    def calc_layout(self):
        self.expr_h = 80
        self.status_h = 20
        remaining = self.HEIGHT - self.expr_h - self.status_h

        top_has = self.show['waveform'] or self.show['bits']
        bot_has = self.show['phase'] or self.show['spectrogram']
        n_rows = (1 if top_has else 0) + (1 if bot_has else 0)
        if n_rows == 0:
            n_rows = 1
        self.row_h = max(20, remaining // n_rows)

        self.rects = {}
        self.panel_surfaces = {}

        # Top row: waveform (left), bits (right)
        y = 0
        if top_has:
            nw = self.show['waveform'] + self.show['bits']
            cw = self.WIDTH // nw if nw > 0 else self.WIDTH
            cx = 0
            if self.show['waveform']:
                self.rects['waveform'] = pygame.Rect(cx, y, cw, self.row_h)
                self.panel_surfaces['waveform'] = None
                cx += cw
            if self.show['bits']:
                self.rects['bits'] = pygame.Rect(cx, y, self.WIDTH - cx, self.row_h)
                self.panel_surfaces['bits'] = None
            y += self.row_h

        # Expression bar (in the middle)
        self.expr_y = y
        y += self.expr_h

        # Bottom row: phase (left), spectrogram (right)
        if bot_has:
            nw = self.show['phase'] + self.show['spectrogram']
            cw = self.WIDTH // nw if nw > 0 else self.WIDTH
            cx = 0
            if self.show['phase']:
                self.rects['phase'] = pygame.Rect(cx, y, cw, self.row_h)
                self.panel_surfaces['phase'] = None
                cx += cw
            if self.show['spectrogram']:
                self.rects['spectrogram'] = pygame.Rect(cx, y, self.WIDTH - cx, self.row_h)
                self.panel_surfaces['spectrogram'] = None

    def run(self):
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            self.render()
            pygame.display.flip()
            self.clock.tick(30)

    def panel_surface(self, name):
        r = self.rects[name]
        s = self.panel_surfaces[name]
        if s is None or s.get_width() != r.w or s.get_height() != r.h:
            s = pygame.Surface((r.w, r.h))
            s.set_colorkey(None)
            self.panel_surfaces[name] = s
        return s

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.quit()
        elif event.type == pygame.VIDEORESIZE:
            self.WIDTH = max(400, event.w)
            self.HEIGHT = max(200, event.h)
            self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), pygame.RESIZABLE)
            self.calc_layout()
            self.phase_grid = None
        elif event.type == pygame.KEYDOWN:
            self.on_key(event)

    def on_key(self, event):
        ch = event.unicode
        key = event.key

        if key == pygame.K_BACKSPACE:
            ch = '\x7f'
        elif key == pygame.K_LEFT:
            ch = 'h'
        elif key == pygame.K_RIGHT:
            ch = 'l'
        elif key == pygame.K_UP:
            ch = 'k'
        elif key == pygame.K_DOWN:
            ch = 'j'
        elif key == pygame.K_ESCAPE:
            self.fuzzy_find()
            return
        elif key == pygame.K_F1:
            self.show_help()
            return
        elif key == pygame.K_SLASH and pygame.key.get_mods() & pygame.KMOD_SHIFT:
            ch = '?'

        mods = pygame.key.get_mods()
        ctrl = mods & pygame.KMOD_CTRL

        if ctrl and key == pygame.K_r:
            self.load_random_preset()
            return
        if ch in (']', 'n'):
            self.load_next_preset(1)
            return
        if ch in ('[', 'p'):
            self.load_next_preset(-1)
            return

        if ch == 'q':
            self.quit()
            return
        if ch == 'r':
            self.engine.reset()
            return
        if ch == 's':
            self.engine.signed_mode = not self.engine.signed_mode
            return
        if ch == '?':
            self.show_help()
            return
        if ch == ':':
            self.fuzzy_find()
            return

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
                    self.save_msg = "[ Saved ]"
                except Exception as e:
                    self.save_msg = f"[ Error: {e} ]"
                self.save_msg_time = time.time()
            elif ch == '\x7f':
                if editor.cursor > 0:
                    editor.save_to_undo()
                    if editor.cursor >= 2 and editor.buf[editor.cursor - 2:editor.cursor] in ('<<', '>>'):
                        editor.buf = editor.buf[:editor.cursor - 2] + editor.buf[editor.cursor:]
                        editor.cursor -= 2
                    else:
                        editor.buf = editor.buf[:editor.cursor - 1] + editor.buf[editor.cursor:]
                        editor.cursor -= 1
            elif ch == 'x' and editor.buf:
                editor.save_to_undo()
                op, op_start, op_len = editor.get_operator_at(editor.buf, editor.cursor)
                if op:
                    editor.buf = editor.buf[:op_start] + editor.buf[op_start + op_len:]
                    editor.cursor = min(op_start, len(editor.buf))
                else:
                    if editor.cursor < len(editor.buf):
                        editor.buf = editor.buf[:editor.cursor] + editor.buf[editor.cursor + 1:]
                    if editor.cursor >= len(editor.buf) and editor.cursor > 0:
                        editor.cursor = len(editor.buf)
            elif ch in ('j', 'k') and editor.buf:
                if editor.cursor < len(editor.buf):
                    editor.save_to_undo()
                    dir_val = 1 if ch == 'k' else -1
                    op, op_start, op_len = editor.get_operator_at(editor.buf, editor.cursor)
                    if op:
                        idx = editor.OPERATORS.index(op)
                        new_op = editor.OPERATORS[(idx + dir_val) % len(editor.OPERATORS)]
                        editor.buf = editor.buf[:op_start] + new_op + editor.buf[op_start + op_len:]
                        editor.cursor = op_start
                    elif editor.buf[editor.cursor].lower() in editor.HEX_CHARS:
                        idx = editor.HEX_CHARS.index(editor.buf[editor.cursor].lower())
                        editor.buf = editor.buf[:editor.cursor] + editor.HEX_CHARS[(idx + dir_val) % 16] + editor.buf[editor.cursor + 1:]
            elif ch in ('<', '>'):
                editor.save_to_undo()
                ins = "<<" if ch == '<' else ">>"
                editor.buf = editor.buf[:editor.cursor] + ins + editor.buf[editor.cursor:]
                editor.cursor += 2
            elif len(ch) == 1 and ch.isprintable():
                u_ch = ch.lower()
                if u_ch not in ('w', 'u', 'q', 'r', 's') and (u_ch in editor.HEX_CHARS or ch in ('t', ' ', ',') or ch in editor.OPERATORS):
                    editor.save_to_undo()
                    editor.buf = editor.buf[:editor.cursor] + ch + editor.buf[editor.cursor:]
                    editor.cursor += 1

    def do_dialog(self, prompt, items):
        """Modal dialog: type to filter, up/down to select, Enter to confirm, Esc to cancel."""
        if not items:
            return None
        query = ""
        selected = 0
        filtered = list(items)
        font = self.font
        small = self.small_font
        overlay = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        box_h = min(240, self.HEIGHT - 80)
        max_show = (box_h - 36) // 16

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                    return None
                if event.type == pygame.KEYDOWN:
                    ch = event.unicode
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key == pygame.K_RETURN:
                        if filtered:
                            return filtered[selected]
                        return None
                    # Navigation: arrows and vim keys
                    if event.key in (pygame.K_UP,):
                        selected = max(0, selected - 1)
                    elif event.key in (pygame.K_DOWN,):
                        selected = min(len(filtered) - 1, selected + 1)
                    elif ch == 'k':
                        selected = max(0, selected - 1)
                    elif ch == 'j':
                        selected = min(len(filtered) - 1, selected + 1)
                    elif ch == 'h':
                        max_show = (box_h - 36) // 16
                        selected = max(0, selected - max_show)
                    elif ch == 'l':
                        max_show = (box_h - 36) // 16
                        selected = min(len(filtered) - 1, selected + max_show)
                    elif event.key == pygame.K_BACKSPACE:
                        query = query[:-1]
                    elif ch and ch in editor.HEX_CHARS + 't, &|^+-*/%<>':
                        query += ch
                    filtered = [p for p in items if query.lower() in p.lower()]
                    if filtered:
                        selected = min(selected, len(filtered) - 1)
                    else:
                        selected = 0

            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (0, 0))

            # Search box
            sx, sy = self.WIDTH // 2 - 200, self.HEIGHT // 2 - 120
            pygame.draw.rect(self.screen, (0x11, 0x11, 0x11), (sx, sy, 400, box_h))
            pygame.draw.rect(self.screen, (0x33, 0x33, 0x33), (sx, sy, 400, box_h), 1)

            # Prompt + cursor
            txt = font.render(prompt + query + "\u2588", True, (0xff, 0xff, 0xff))
            self.screen.blit(txt, (sx + 8, sy + 6))

            # Filtered list
            scroll = max(0, selected - max_show + 1) if selected >= max_show else 0
            visible = filtered[scroll:scroll + max_show]
            for i, item in enumerate(visible):
                y = sy + 30 + i * 16
                if scroll + i == selected:
                    pygame.draw.rect(self.screen, (0x55, 0x55, 0x55), (sx + 4, y, 392, 16))
                txt = small.render(item, True, (0xcc, 0xcc, 0xcc))
                self.screen.blit(txt, (sx + 8, y))

            if not filtered:
                txt = small.render("(no matches)", True, (0x66, 0x66, 0x66))
                self.screen.blit(txt, (sx + 8, sy + 30))

            pygame.display.flip()
            self.clock.tick(30)

    def fuzzy_find(self):
        try:
            with open("bytebeat_presets.txt", "r") as f:
                presets = [line.rstrip('\n') for line in f if line.strip()]
        except FileNotFoundError:
            return
        if not presets:
            return
        result = self.do_dialog(":", presets)
        if result is not None:
            with editor.buffer_lock:
                editor.save_to_undo()
                editor.buf = result
                editor.cursor = len(result)

    def show_help(self):
        try:
            with open("help.txt", "r") as f:
                lines = [line.rstrip('\n') for line in f if line.strip()]
        except FileNotFoundError:
            lines = ["Help file not found."]
        if lines:
            self.do_dialog("? ", lines)

    def load_next_preset(self, direction):
        presets = editor.load_presets()
        if not presets:
            return
        self.preset_idx = (self.preset_idx + direction) % len(presets)
        with editor.buffer_lock:
            editor.save_to_undo()
            editor.buf = presets[self.preset_idx]
            editor.cursor = len(editor.buf)

    def load_random_preset(self):
        presets = editor.load_presets()
        if not presets:
            return
        with editor.buffer_lock:
            editor.save_to_undo()
            editor.buf = random.choice(presets)
            editor.cursor = len(editor.buf)

    def quit(self):
        self.running = False
        self.stream.stop()
        self.stream.close()
        pygame.quit()

    def render(self):
        self.screen.fill((0, 0, 0))

        with editor.buffer_lock:
            local_buf = editor.buf
            local_cursor = editor.cursor

        with self.engine.telemetry_lock:
            local_log_t = list(self.engine.log_t)
            local_log_o = list(self.engine.log_o)

        samples = list(self.engine.samples)

        self.render_expression(local_buf, local_cursor, self.engine.signed_mode)

        if self.show['waveform']:
            self.render_waveform(samples)
        if self.show['phase']:
            self.render_phase(samples)
        if self.show['bits']:
            self.render_bits(samples)
        if self.show['spectrogram']:
            self.render_spectrogram(samples)

        self.render_status(local_log_t, local_log_o)

    # ── expression bar ──────────────────────────────────────────────

    def render_expression(self, buf, cursor, signed_mode):
        r = pygame.Rect(0, self.expr_y, self.WIDTH, self.expr_h)
        self.screen.fill((0x11, 0x11, 0x11), r)

        tokens = re.split(r'(<<|>>|[\s\&\|\^\+\-\/\*\%t\,])', buf)
        cw = self.char_w
        font_h = self.big_font.size('M')[1]
        x = 16
        y = self.expr_y + (self.expr_h - font_h) // 2
        char_count = 0

        if signed_mode:
            s = self.big_font.render("SIGNED ", True, (0xff, 0xff, 0xff))
            self.screen.blit(s, (x, y))
            x += s.get_width()

        for token in tokens:
            if not token:
                continue
            is_op = token in editor.OPERATORS or token == 't'
            for ch in token:
                if char_count == cursor:
                    pygame.draw.rect(self.screen, (0x55, 0x55, 0x55), (x, y - 1, cw, font_h))
                color = (0xff, 0xff, 0xff) if is_op else (0xcc, 0xcc, 0xcc)
                s = self.big_font.render(ch, True, color)
                self.screen.blit(s, (x, y))
                x += cw
                char_count += 1

        if cursor >= len(buf):
            pygame.draw.rect(self.screen, (0x55, 0x55, 0x55), (x, y - 1, cw, font_h))

    # ── status bar ──────────────────────────────────────────────────

    def render_status(self, log_t, log_o):
        r = pygame.Rect(0, self.HEIGHT - self.status_h, self.WIDTH, self.status_h)
        self.screen.fill((0, 0, 0), r)

        parts = []
        for t, o in zip(log_t[:3], log_o[:3]):
            t_hex = t[4:12]
            o_hex = o[5:7]
            parts.append(f"{t_hex}:{o_hex}")
        text = "  ".join(parts)

        if self.save_msg and (time.time() - self.save_msg_time < 2):
            text += f"   {self.save_msg}"
        else:
            self.save_msg = ""

        s = self.small_font.render(text, True, (0x66, 0x66, 0x66))
        self.screen.blit(s, (8, self.HEIGHT - self.status_h + 4))

    # ── waveform ────────────────────────────────────────────────────

    def render_waveform(self, samples):
        r = self.rects['waveform']
        w, h = r.w, r.h
        if w < 10 or h < 10:
            return

        margin = 4
        y0 = r.y + margin
        y1 = r.y + h - margin

        # Guide lines
        for val in (0x00, 0x80, 0xFF):
            y = y0 + (1.0 - val / 255.0) * (y1 - y0)
            pygame.draw.line(self.screen, (0x22, 0x22, 0x22), (r.x, y), (r.x + w, y))
            s = self.small_font.render(f"0x{val:02X}", True, (0x44, 0x44, 0x44))
            self.screen.blit(s, (r.x + 2, y - 6))

        if not samples or len(samples) < 2:
            return

        plot_w = w - 30
        if plot_w <= 0:
            return

        n = len(samples)
        step = max(1, n // plot_w)
        pts = samples[::step][:plot_w]

        coords = []
        for i, v in enumerate(pts):
            x = r.x + 28 + i
            y = y0 + (1.0 - v / 255.0) * (y1 - y0)
            coords.append((x, y))

        if len(coords) >= 2:
            pygame.draw.lines(self.screen, (0xff, 0xff, 0xff), False, coords, 1)

        if pts:
            mn = min(pts)
            mx = max(pts)
            s = self.small_font.render(f"min:0x{mn:02X}", True, (0x66, 0x66, 0x66))
            self.screen.blit(s, (r.x + w - 2 - s.get_width(), y0))
            s = self.small_font.render(f"peak:0x{mx:02X}", True, (0x66, 0x66, 0x66))
            self.screen.blit(s, (r.x + w - 2 - s.get_width(), y1 - 12))

    # ── phase portrait ──────────────────────────────────────────────

    PHASE_GW = 80
    PHASE_GH = 24

    def render_phase(self, samples):
        r = self.rects['phase']
        w, h = r.w, r.h
        if w < 10 or h < 10:
            return

        gw, gh = self.PHASE_GW, self.PHASE_GH

        if w != self.phase_w or h != self.phase_h:
            self.phase_w = w
            self.phase_h = h
            self.phase_grid = np.zeros((gh, gw), dtype=np.float32)

        grid = self.phase_grid
        grid *= 0.95

        for i in range(len(samples) - 1):
            gx = int(samples[i]) * gw // 256
            gy = (255 - int(samples[i + 1])) * gh // 256
            if 0 <= gx < gw and 0 <= gy < gh:
                grid[gy, gx] += 1.0

        max_val = grid.max()
        if max_val < 0.01:
            max_val = 1.0

        # Non-linear scaling (sqrt) to bring out subtle patterns
        norm = grid / max_val
        enhanced = np.sqrt(norm)
        scaled = (enhanced * 255).astype(np.uint8)

        # Upscale to canvas size via nearest-neighbor
        x_idx = np.arange(w) * gw // w
        y_idx = np.arange(h) * gh // h
        up = scaled[np.ix_(y_idx, x_idx)]  # shape (h, w)

        arr = np.zeros((w, h, 3), dtype=np.uint8)
        arr[:, :, 0] = up.T
        arr[:, :, 1] = up.T
        arr[:, :, 2] = up.T

        surface = self.panel_surface('phase')
        pygame.surfarray.blit_array(surface, arr)
        self.screen.blit(surface, (r.x, r.y))

    # ── bit planes ──────────────────────────────────────────────────

    def render_bits(self, samples):
        r = self.rects['bits']
        w, h = r.w, r.h
        if w < 10 or h < 10:
            return

        recent = list(samples)[-w:] if samples else []
        band_h = max(1, h // 8)

        arr = np.zeros((w, h, 3), dtype=np.uint8)
        for bit_row in range(8):
            bit = 7 - bit_row
            y0_b = bit_row * band_h
            y1_b = min(y0_b + band_h, h)
            for x in range(min(w, len(recent))):
                if (int(recent[x]) >> bit) & 1:
                    arr[x, y0_b:y1_b, :] = 255

        surface = self.panel_surface('bits')
        pygame.surfarray.blit_array(surface, arr)
        self.screen.blit(surface, (r.x, r.y))

    # ── spectrogram ─────────────────────────────────────────────────

    def render_spectrogram(self, samples):
        r = self.rects['spectrogram']
        w, h = r.w, r.h
        if w < 2 or h < 2:
            return

        self.spec_raw.extend(samples)
        while self.spec_next_fft + FFT_SIZE <= len(self.spec_raw):
            chunk = self.spec_raw[self.spec_next_fft:self.spec_next_fft + FFT_SIZE]
            window = np.array(chunk, dtype=float)
            window *= np.hanning(FFT_SIZE)
            mag = np.abs(np.fft.rfft(window))
            mx = mag.max()
            if mx > 1e-10:
                mag_norm = np.sqrt(mag / mx)
            else:
                mag_norm = np.zeros_like(mag)
            scaled = (mag_norm * 255).astype(np.uint8)
            self.spec_cols.append(scaled)
            self.spec_next_fft += SPEC_HOP

        if len(self.spec_raw) > 4096:
            excess = len(self.spec_raw) - 2048
            self.spec_raw = self.spec_raw[excess:]
            self.spec_next_fft -= excess
            if self.spec_next_fft < 0:
                self.spec_next_fft = 0

        while len(self.spec_cols) > w:
            self.spec_cols.pop(0)

        if not self.spec_cols:
            return

        n_bins = len(self.spec_cols[0])

        arr = np.zeros((w, h, 3), dtype=np.uint8)
        for y in range(h):
            bin_idx = y * n_bins // h
            if bin_idx >= n_bins:
                bin_idx = n_bins - 1
            for col_idx, col in enumerate(self.spec_cols):
                if bin_idx < len(col):
                    v = int(col[bin_idx])
                else:
                    v = 0
                arr[col_idx, y, :] = v

        surface = self.panel_surface('spectrogram')
        pygame.surfarray.blit_array(surface, arr)
        self.screen.blit(surface, (r.x, r.y))

        s = self.small_font.render("dB", True, (0x44, 0x44, 0x44))
        self.screen.blit(s, (r.x + 4, r.y + 2))
        s = self.small_font.render("0", True, (0x44, 0x44, 0x44))
        self.screen.blit(s, (r.x + 4, r.y + h - 14))


def main():
    parser = argparse.ArgumentParser(description='sbb bytebeat editor (GUI)')
    parser.add_argument('--rate', type=int, default=8000,
                        help='Sample rate in Hz (default: 8000)')
    parser.add_argument('--no-waveform', action='store_true',
                        help='Disable waveform display')
    parser.add_argument('--no-phase', action='store_true',
                        help='Disable phase portrait')
    parser.add_argument('--no-bits', action='store_true',
                        help='Disable bit planes')
    parser.add_argument('--no-spectrogram', action='store_true',
                        help='Disable spectrogram')
    args = parser.parse_args()

    app = SBBGui(args)
    app.run()


if __name__ == '__main__':
    main()
