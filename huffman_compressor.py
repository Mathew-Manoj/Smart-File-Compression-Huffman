"""
Smart File Compression Tool using Huffman Coding
D&A Assignment 2 | Mathew Manoj | Roll No. 23

Run: python huffman_compressor.py
Requires only Python 3 (Tkinter is included with most desktop Python installations).
"""

import heapq
import json
import os
import struct
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import Counter
from dataclasses import dataclass
from typing import Optional


MAGIC = b"HUF1"


@dataclass
class Node:
    freq: int
    symbol: Optional[int] = None
    left: Optional["Node"] = None
    right: Optional["Node"] = None

    @property
    def is_leaf(self):
        return self.symbol is not None


def build_huffman_tree(data: bytes):
    """Build a deterministic Huffman tree and return (root, merge_steps)."""
    if not data:
        return None, []
    counts = Counter(data)
    heap = []
    serial = 0
    for symbol, freq in sorted(counts.items()):
        heapq.heappush(heap, (freq, serial, Node(freq, symbol=symbol)))
        serial += 1

    steps = []
    while len(heap) > 1:
        f1, _, left = heapq.heappop(heap)
        f2, _, right = heapq.heappop(heap)
        parent = Node(f1 + f2, left=left, right=right)
        steps.append({
            "left": describe_node(left),
            "right": describe_node(right),
            "combined": f1 + f2,
            "remaining": len(heap) + 1
        })
        heapq.heappush(heap, (parent.freq, serial, parent))
        serial += 1
    return heap[0][2], steps


def describe_node(node):
    if node.is_leaf:
        return f"{symbol_label(node.symbol)} ({node.freq})"
    return f"Node ({node.freq})"


def symbol_label(value):
    if value == 32:
        return "SPACE"
    if value == 10:
        return "LF"
    if value == 13:
        return "CR"
    if 32 <= value <= 126:
        return repr(chr(value))
    return f"0x{value:02X}"


def make_codes(root):
    codes = {}
    if root is None:
        return codes

    def walk(node, prefix):
        if node.is_leaf:
            # A one-symbol input still needs one bit per symbol.
            codes[node.symbol] = prefix or "0"
            return
        walk(node.left, prefix + "0")
        walk(node.right, prefix + "1")

    walk(root, "")
    return codes


def encode_bytes(data: bytes, codes):
    bit_string = "".join(codes[b] for b in data)
    padding = (8 - len(bit_string) % 8) % 8
    bit_string += "0" * padding
    packed = bytes(
        int(bit_string[i:i + 8], 2)
        for i in range(0, len(bit_string), 8)
    ) if bit_string else b""
    return packed, len(bit_string) - padding, padding


def compress_bytes(data: bytes):
    root, steps = build_huffman_tree(data)
    if not data:
        header = {"frequencies": {}, "bit_length": 0, "original_size": 0}
        return MAGIC + struct.pack(">I", len(json.dumps(header).encode())) + json.dumps(header).encode(), root, {}, steps

    frequencies = Counter(data)
    codes = make_codes(root)
    packed, bit_length, padding = encode_bytes(data, codes)
    header = {
        "frequencies": {str(k): v for k, v in frequencies.items()},
        "bit_length": bit_length,
        "original_size": len(data)
    }
    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    result = MAGIC + struct.pack(">I", len(header_bytes)) + header_bytes + packed
    return result, root, codes, steps


def decompress_bytes(blob: bytes):
    if len(blob) < 8 or blob[:4] != MAGIC:
        raise ValueError("This is not a valid HUF1 compressed file.")
    header_len = struct.unpack(">I", blob[4:8])[0]
    if header_len > len(blob) - 8:
        raise ValueError("Corrupt file: invalid header length.")
    header = json.loads(blob[8:8 + header_len].decode("utf-8"))
    payload = blob[8 + header_len:]
    frequencies = {int(k): int(v) for k, v in header["frequencies"].items()}
    expected_size = int(header["original_size"])
    bit_length = int(header["bit_length"])

    if expected_size == 0:
        return b""
    heap = []
    serial = 0
    for symbol, freq in sorted(frequencies.items()):
        if freq <= 0 or not 0 <= symbol <= 255:
            raise ValueError("Corrupt file: invalid frequency table.")
        heapq.heappush(heap, (freq, serial, Node(freq, symbol=symbol)))
        serial += 1
    if not heap:
        raise ValueError("Corrupt file: missing frequency table.")
    while len(heap) > 1:
        f1, _, left = heapq.heappop(heap)
        f2, _, right = heapq.heappop(heap)
        heapq.heappush(heap, (f1 + f2, serial, Node(f1 + f2, left=left, right=right)))
        serial += 1
    root = heap[0][2]

    if root.is_leaf:
        return bytes([root.symbol]) * expected_size

    out = bytearray()
    node = root
    consumed = 0
    for byte in payload:
        for shift in range(7, -1, -1):
            if consumed >= bit_length:
                break
            bit = (byte >> shift) & 1
            node = node.left if bit == 0 else node.right
            if node is None:
                raise ValueError("Corrupt file: invalid Huffman path.")
            if node.is_leaf:
                out.append(node.symbol)
                node = root
            consumed += 1
        if consumed >= bit_length:
            break
    if len(out) != expected_size:
        raise ValueError("Corrupt or incomplete file: decoded size does not match.")
    return bytes(out)


class HuffmanApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart File Compression Tool | Huffman Coding")
        self.root.geometry("1120x760")
        self.root.minsize(900, 650)
        self.data = b""
        self.tree = None
        self.codes = {}
        self.steps = []
        self.step_index = 0
        self.current_file = None

        self._style()
        self._build_ui()
        self._show_welcome()

    def _style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 10))
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=7)
        style.configure("Treeview", rowheight=25, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="SMART FILE COMPRESSION TOOL", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Huffman Coding • Greedy Algorithm • DAA Assignment 2", style="Sub.TLabel").pack(anchor="w")

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Open File", command=self.open_file, style="Action.TButton").pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Compress Text", command=self.compress_text, style="Action.TButton").pack(side="left", padx=6)
        ttk.Button(actions, text="Compress File", command=self.compress_file, style="Action.TButton").pack(side="left", padx=6)
        ttk.Button(actions, text="Decompress .huf", command=self.decompress_file, style="Action.TButton").pack(side="left", padx=6)
        ttk.Button(actions, text="Clear", command=self.clear, style="Action.TButton").pack(side="left", padx=6)

        paned = ttk.Panedwindow(outer, orient="horizontal")
        paned.pack(fill="both", expand=True)

        left = ttk.Frame(paned, padding=(0, 0, 8, 0))
        right = ttk.Frame(paned, padding=(8, 0, 0, 0))
        paned.add(left, weight=3)
        paned.add(right, weight=4)

        ttk.Label(left, text="Input text / file preview", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.input_text = tk.Text(left, height=12, wrap="word", font=("Consolas", 10), undo=True)
        self.input_text.pack(fill="both", expand=True, pady=(5, 10))
        self.input_text.insert("1.0", "Huffman coding is a greedy algorithm that assigns shorter codes to more frequent symbols.")

        self.stats = ttk.LabelFrame(left, text="Compression statistics", padding=10)
        self.stats.pack(fill="x", pady=(0, 10))
        self.stats_var = tk.StringVar(value="Load or enter text, then choose Compress Text.")
        ttk.Label(self.stats, textvariable=self.stats_var, justify="left", wraplength=350).pack(anchor="w")

        ttk.Label(left, text="Huffman code table", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.code_table = ttk.Treeview(left, columns=("symbol", "frequency", "code"), show="headings", height=8)
        for col, title, width in [("symbol", "Byte / symbol", 120), ("frequency", "Frequency", 85), ("code", "Huffman code", 150)]:
            self.code_table.heading(col, text=title)
            self.code_table.column(col, width=width, anchor="center")
        self.code_table.pack(fill="x", pady=(5, 0))

        ttk.Label(right, text="Algorithm visualization", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.canvas = tk.Canvas(right, height=340, background="#101820", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=(5, 8))
        self.canvas.bind("<Configure>", lambda _e: self.draw_tree())

        step_frame = ttk.LabelFrame(right, text="Step-by-step execution", padding=9)
        step_frame.pack(fill="x", pady=(0, 8))
        self.step_var = tk.StringVar(value="The algorithm repeatedly combines the two nodes with the lowest frequencies.")
        ttk.Label(step_frame, textvariable=self.step_var, wraplength=570, justify="left").pack(anchor="w")
        controls = ttk.Frame(step_frame)
        controls.pack(fill="x", pady=(8, 0))
        self.prev_btn = ttk.Button(controls, text="◀ Previous", command=self.previous_step, state="disabled")
        self.prev_btn.pack(side="left")
        self.next_btn = ttk.Button(controls, text="Next Step ▶", command=self.next_step, state="disabled")
        self.next_btn.pack(side="left", padx=6)
        self.step_count = ttk.Label(controls, text="Step 0 / 0")
        self.step_count.pack(side="right")

        info = ttk.LabelFrame(right, text="Algorithm & complexity", padding=9)
        info.pack(fill="x")
        ttk.Label(
            info,
            text=("Greedy choice: repeatedly merge the two least-frequent nodes. "
                  "A binary tree gives each byte a prefix-free code (0 = left, 1 = right).\n"
                  "Time: O(n + k log k) including frequency counting and tree construction; "
                  "encoding is O(n). Space: O(k + n) including tree, code table and output.\n"
                  "n = number of input bytes; k = number of distinct byte values (k ≤ 256)."),
            wraplength=570, justify="left"
        ).pack(anchor="w")

        self.status = tk.StringVar(value="Ready")
        ttk.Label(outer, textvariable=self.status, relief="sunken", anchor="w").pack(fill="x", pady=(9, 0))

    def _show_welcome(self):
        self.canvas.create_text(20, 25, anchor="nw", fill="#d7e7f5",
            text="Tree visualization will appear after compression.", font=("Segoe UI", 12))
        self.canvas.create_text(20, 55, anchor="nw", fill="#8fb6d8",
            text="Use Open File for any file, or edit the sample text and click Compress Text.",
            font=("Segoe UI", 9))

    def open_file(self):
        path = filedialog.askopenfilename(title="Choose a file")
        if not path:
            return
        try:
            with open(path, "rb") as f:
                self.data = f.read()
            self.current_file = path
            # Show readable preview where possible; binary data is represented safely.
            preview = self.data[:12000].decode("utf-8", errors="replace")
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", preview)
            self.status.set(f"Loaded {os.path.basename(path)} ({len(self.data):,} bytes)")
            self.stats_var.set(f"Loaded file: {os.path.basename(path)}\nSize: {len(self.data):,} bytes\nClick Compress File to create a .huf archive.")
        except OSError as exc:
            messagebox.showerror("File error", str(exc))

    def _fill_table(self):
        for item in self.code_table.get_children():
            self.code_table.delete(item)
        frequencies = Counter(self.data)
        for symbol in sorted(frequencies):
            self.code_table.insert("", "end", values=(symbol_label(symbol), frequencies[symbol], self.codes.get(symbol, "")))

    def _prepare(self, data):
        self.data = data
        self.tree, self.steps = build_huffman_tree(data)
        self.codes = make_codes(self.tree)
        self.step_index = 0
        self._fill_table()
        self.draw_tree()
        self._update_step()

    def compress_text(self):
        text = self.input_text.get("1.0", "end-1c")
        data = text.encode("utf-8")
        if not data:
            messagebox.showinfo("Empty input", "Enter some text before compressing.")
            return
        self._prepare(data)
        blob, _, _, _ = compress_bytes(data)
        original = len(data)
        compressed = len(blob)
        ratio = (1 - compressed / original) * 100
        self.stats_var.set(
            f"Original UTF-8 size: {original:,} bytes\n"
            f"Compressed archive size: {compressed:,} bytes\n"
            f"Archive size change: {ratio:+.1f}% (negative means the archive is larger)\n"
            f"Distinct byte values: {len(self.codes)}"
        )
        self.status.set("Text encoded successfully. Use Compress File to save a .huf archive.")
        self.last_blob = blob

    def compress_file(self):
        if self.current_file and os.path.exists(self.current_file):
            source = self.current_file
            with open(source, "rb") as f:
                data = f.read()
            default = os.path.basename(source) + ".huf"
        else:
            data = self.input_text.get("1.0", "end-1c").encode("utf-8")
            if not data:
                messagebox.showinfo("Empty input", "Load a file or enter text first.")
                return
            default = "compressed.huf"
            source = None
        blob, tree, codes, steps = compress_bytes(data)
        target = filedialog.asksaveasfilename(
            title="Save compressed archive", defaultextension=".huf",
            initialfile=default, filetypes=[("Huffman archive", "*.huf"), ("All files", "*.*")]
        )
        if not target:
            return
        try:
            with open(target, "wb") as f:
                f.write(blob)
            self.current_file = source
            self._prepare(data)
            original = len(data)
            compressed = len(blob)
            change = (1 - compressed / original) * 100 if original else 0
            self.stats_var.set(
                f"Original size: {original:,} bytes\nCompressed archive: {compressed:,} bytes\n"
                f"Archive size change: {change:+.1f}%\nDistinct byte values: {len(codes)}"
            )
            self.status.set(f"Saved compressed file: {target}")
            messagebox.showinfo("Compression complete", f"Saved:\n{target}\n\n{original:,} → {compressed:,} bytes")
        except OSError as exc:
            messagebox.showerror("Save error", str(exc))

    def decompress_file(self):
        source = filedialog.askopenfilename(title="Choose .huf archive", filetypes=[("Huffman archive", "*.huf"), ("All files", "*.*")])
        if not source:
            return
        try:
            with open(source, "rb") as f:
                blob = f.read()
            restored = decompress_bytes(blob)
            suggested = os.path.basename(source)
            if suggested.endswith(".huf"):
                suggested = suggested[:-4]
            target = filedialog.asksaveasfilename(
                title="Save decompressed file", initialfile=suggested,
                filetypes=[("All files", "*.*")]
            )
            if not target:
                return
            with open(target, "wb") as f:
                f.write(restored)
            self.data = restored
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", restored[:12000].decode("utf-8", errors="replace"))
            self.status.set(f"Decompressed successfully: {target}")
            messagebox.showinfo("Decompression complete", f"Restored {len(restored):,} bytes to:\n{target}")
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            messagebox.showerror("Decompression error", str(exc))

    def _update_step(self):
        total = len(self.steps)
        if total == 0:
            self.step_var.set("Only one distinct byte value (or empty input): no merging is required. Each symbol receives a valid code.")
            self.step_count.config(text="Step 0 / 0")
            self.prev_btn.config(state="disabled")
            self.next_btn.config(state="disabled")
        else:
            if self.step_index == 0:
                self.step_var.set(f"Start: {len(self.codes)} distinct byte values are represented as leaf nodes. Select the two smallest frequencies.")
            else:
                s = self.steps[self.step_index - 1]
                self.step_var.set(
                    f"Merge {self.step_index}: combine {s['left']} and {s['right']} "
                    f"into a parent node with frequency {s['combined']}. "
                    f"Insert the parent back into the min-priority queue."
                )
            self.step_count.config(text=f"Step {self.step_index} / {total}")
            self.prev_btn.config(state="normal" if self.step_index > 0 else "disabled")
            self.next_btn.config(state="normal" if self.step_index < total else "disabled")
        self.draw_tree()

    def previous_step(self):
        self.step_index = max(0, self.step_index - 1)
        self._update_step()

    def next_step(self):
        self.step_index = min(len(self.steps), self.step_index + 1)
        self._update_step()

    def draw_tree(self):
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 500)
        if self.tree is None:
            self._show_welcome()
            return

        # Show the actual final Huffman tree; step controls explain each greedy merge.
        positions = {}
        leaves = []
        def collect(node, depth=0):
            if node.is_leaf:
                leaves.append(node)
                return
            collect(node.left, depth + 1)
            collect(node.right, depth + 1)
        collect(self.tree)
        leaf_x = {}
        count = max(1, len(leaves))
        for i, leaf in enumerate(leaves):
            leaf_x[id(leaf)] = 35 + i * (width - 70) / max(1, count - 1) if count > 1 else width / 2

        cursor = [0]
        def layout(node, depth=0):
            if node.is_leaf:
                x = leaf_x[id(node)]
            else:
                layout(node.left, depth + 1)
                layout(node.right, depth + 1)
                x = (positions[id(node.left)][0] + positions[id(node.right)][0]) / 2
            y = 35 + depth * 62
            positions[id(node)] = (x, y)
        layout(self.tree)

        def render(node):
            x, y = positions[id(node)]
            for child, bit in ((node.left, "0"), (node.right, "1")):
                if child:
                    cx, cy = positions[id(child)]
                    self.canvas.create_line(x, y + 15, cx, cy - 15, fill="#6d9fbd", width=2)
                    self.canvas.create_text((x + cx) / 2, (y + cy) / 2, text=bit, fill="#ffd166", font=("Segoe UI", 9, "bold"))
                    render(child)
            label = str(node.freq) if not node.is_leaf else f"{symbol_label(node.symbol)}\n{node.freq}"
            fill = "#245b7a" if not node.is_leaf else "#28664f"
            self.canvas.create_oval(x - 25, y - 16, x + 25, y + 16, fill=fill, outline="#d7e7f5", width=1)
            self.canvas.create_text(x, y, text=label, fill="white", font=("Segoe UI", 8, "bold"))
        render(self.tree)
        self.canvas.create_text(12, self.canvas.winfo_height() - 12, anchor="sw",
            text="Final Huffman tree  •  left edge = 0  •  right edge = 1",
            fill="#9bbbd0", font=("Segoe UI", 8))

    def clear(self):
        self.input_text.delete("1.0", "end")
        self.data = b""
        self.tree = None
        self.codes = {}
        self.steps = []
        self.step_index = 0
        for item in self.code_table.get_children():
            self.code_table.delete(item)
        self.stats_var.set("No input loaded.")
        self.step_var.set("Enter text or open a file to begin.")
        self.step_count.config(text="Step 0 / 0")
        self.prev_btn.config(state="disabled")
        self.next_btn.config(state="disabled")
        self.canvas.delete("all")
        self.status.set("Cleared")


def main():
    root = tk.Tk()
    HuffmanApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
