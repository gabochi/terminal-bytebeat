#!/usr/bin/env python3
import argparse
import random
import re
import time

import numpy as np
import pygame

import editor
from engine import RPNEngine
from viz import get_shapes, get_shape_names


class SBB3D:
    def __init__(self, args):
        self.shapes = get_shapes()
        self.args = args
        if args.rate > 8000:
            engine_kwargs = {'sample_rate': args.rate, 't_step': 8000, 't_den': args.rate}
        else:
            engine_kwargs = {'sample_rate': 8000, 't_step': 1, 't_den': 1}
        self.engine = RPNEngine(**engine_kwargs)
        self.save_msg = ""
        self.save_msg_time = 0
        self.preset_idx = -1
        self.angle = 0.0
        self.fov = 500
        self.auto_rotate = True
        self.shape_idx = 0

        pygame.init()
        self.WIDTH, self.HEIGHT = 900, 640
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("sbb \u2014 bytebeat 3D")
        self.clock = pygame.time.Clock()
        self.running = True

        self.big_font = pygame.font.SysFont('monospace', 36)
        self.font = pygame.font.SysFont('monospace', 16)
        self.small_font = pygame.font.SysFont('monospace', 12)

        self.calc_layout()

        import sounddevice as sd
        self.stream = sd.OutputStream(
            channels=1,
            callback=self.engine.callback,
            samplerate=self.engine.SAMPLE_RATE,
            blocksize=self.engine.BUFFER_SIZE,
        )
        self.stream.start()

    @property
    def shape(self):
        return self.shapes[self.shape_idx]

    def calc_layout(self):
        self.expr_h = 80
        self.status_h = 20
        self.view_y = 0
        self.view_h = self.HEIGHT - self.expr_h - self.status_h
        self.expr_y = self.view_h
        self.status_y = self.HEIGHT - self.status_h

    def run(self):
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            self.render()
            pygame.display.flip()
            self.clock.tick(30)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.quit()
        elif event.type == pygame.VIDEORESIZE:
            self.WIDTH = max(400, event.w)
            self.HEIGHT = max(300, event.h)
            self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), pygame.RESIZABLE)
            self.calc_layout()
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
        elif key == pygame.K_TAB:
            self.shape_idx = (self.shape_idx + 1) % len(self.shapes)
            return
        elif key == pygame.K_ESCAPE:
            ch = ':'
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
        if ch == ' ':
            self.auto_rotate = not self.auto_rotate
            return
        if ch == ':':
            self.fuzzy_find()
            return
        if ch == '?':
            self.show_help()
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
        if not self.running:
            return
        self.screen.fill((0, 0, 0))

        with editor.buffer_lock:
            local_buf = editor.buf
            local_cursor = editor.cursor

        with self.engine.telemetry_lock:
            local_log_t = list(self.engine.log_t)
            local_log_o = list(self.engine.log_o)

        samples = list(self.engine.samples)

        shape = self.shape
        shape.deform(samples)

        if self.auto_rotate:
            self.angle += 0.008

        if shape.fixed_cam_dist is not None:
            cam_dist = shape.fixed_cam_dist
        else:
            cam_dist = max(7, shape.radius * 2.0)
        cam_pos = (0, shape.cam_y, -cam_dist)

        v = pygame.Surface((self.WIDTH, self.view_h))
        v.fill((0, 0, 0))
        shape.render(v, self.fov, self.WIDTH, self.view_h, self.angle, cam_pos)
        self.screen.blit(v, (0, self.view_y))

        self.render_expression(local_buf, local_cursor, self.engine.signed_mode)
        self.render_status(local_log_t, local_log_o)

    def render_expression(self, buf, cursor, signed_mode):
        r = pygame.Rect(0, self.expr_y, self.WIDTH, self.expr_h)
        self.screen.fill((0x11, 0x11, 0x11), r)

        tokens = re.split(r'(<<|>>|[\s\&\|\^\+\-\/\*\%t\,])', buf)
        cw = self.big_font.size('M')[0]
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

    def render_status(self, log_t, log_o):
        r = pygame.Rect(0, self.status_y, self.WIDTH, self.status_h)
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

        mode = "SIGNED" if self.engine.signed_mode else "UNSIGNED"
        rot = "AUTO" if self.auto_rotate else "MANUAL"
        text = f"{mode}  {self.shape.name.upper()}  {rot}  {text}"

        s = self.small_font.render(text, True, (0x66, 0x66, 0x66))
        self.screen.blit(s, (8, self.status_y + 4))


    def do_dialog(self, prompt, items):
        if not items:
            return None
        query = ""
        selected = 0
        filtered = list(items)
        font = self.font
        small = self.small_font
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

            overlay = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (0, 0))

            sx, sy = self.WIDTH // 2 - 200, self.HEIGHT // 2 - 120
            pygame.draw.rect(self.screen, (0x11, 0x11, 0x11), (sx, sy, 400, box_h))
            pygame.draw.rect(self.screen, (0x33, 0x33, 0x33), (sx, sy, 400, box_h), 1)

            txt = font.render(prompt + query + "\u2588", True, (0xff, 0xff, 0xff))
            self.screen.blit(txt, (sx + 8, sy + 6))

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


def main():
    parser = argparse.ArgumentParser(description='sbb bytebeat 3D')
    parser.add_argument('--rate', type=int, default=8000)
    args = parser.parse_args()
    app = SBB3D(args)
    app.run()


if __name__ == '__main__':
    main()
