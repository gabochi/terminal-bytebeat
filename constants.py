SAMPLE_RATE = 8000
BUFFER_SIZE = 1024
HEX_CHARS = "0123456789ABCDEF"
SAVE_FILE = "bytebeat_saves.txt"

OP_MAP = {
    '+': '+', '-': '-', '*': '*', '/': '/', '%': '%',
    '&': '&', '|': '|', '^': '^', '<': '<<', '>': '>>', 't': 't'
}
OPERATORS = list(OP_MAP.values())
