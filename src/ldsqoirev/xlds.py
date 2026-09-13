"""Interactive, read-only LDS/CDOC explorer.

This is an inspection aid, not a complete LDS specification.  Its labels are
limited to structures established by the fixture research; every other span is
kept visible as an explicitly unknown cell.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import re
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import zipfile

from .inspect import find_qoi_streams, sha256


MARKER = b"\xad\x9cN\x1e"
HEADER_SIZE = 32


@dataclass
class Node:
    label: str
    start: int
    end: int
    details: list[str] = field(default_factory=list)
    children: list["Node"] = field(default_factory=list)


def _strings(data: bytes) -> list[str]:
    """Return distinct printable runs; useful, but intentionally not a decoder."""
    output: list[str] = []
    run = bytearray()
    for byte in data + b"\0":
        if 32 <= byte <= 126:
            run.append(byte)
        else:
            if len(run) >= 3:
                value = run.decode("ascii", "replace")
                if value not in output:
                    output.append(value)
            run.clear()
    return output[:12]


def _node_for_record(data: bytes, number: int, start: int, next_marker: int) -> Node:
    """Parse one marker-framed cell, conservatively validating its declared span."""
    if start + HEADER_SIZE > len(data):
        return Node(f"[Not Understood #{number:04d}: truncated marker]", start, min(start + 4, len(data)))
    scope, kind, declared, record_id, auxiliary = struct.unpack_from("<IIIII", data, start + 4)
    payload_start = start + HEADER_SIZE
    declared_end = payload_start + declared
    valid_length = declared_end <= len(data) and (next_marker < 0 or declared_end <= next_marker)
    end = declared_end if valid_length else (next_marker if next_marker >= 0 else len(data))
    title = f"Cell #{number} — type {kind}"
    details = [
        f"CDOC offset: 0x{start:08X}",
        f"Span: {end - start:,} bytes (0x{end - start:X})",
        f"Header: scope={scope}, type={kind}, declared payload={declared:,}, record ID={record_id}, auxiliary={auxiliary}",
    ]
    if not valid_length:
        title = f"[Not Understood #{number:04d}: invalid record length]"
        details.append("The declared payload would cross the next marker or end of CDOC; raw cell boundary used.")
    node = Node(title, start, end, details)
    payload = data[payload_start:end]

    if kind == 100 and declared >= 48 and valid_length:
        title = f"Cell #{number} — Object / placement (type 100)"
        node.label = title
        width, height = struct.unpack_from("<ff", data, start + 44)
        node.children.append(Node("Source extent (observed)", start + 44, start + 52, [f"width={width:.7g}, height={height:.7g}"]))
        if declared >= 48:
            a, b, c, d = struct.unpack_from("<ffff", data, start + 64)
            node.children.append(Node("Scaling / rotation matrix (observed)", start + 64, start + 80,
                                      [f"[[{a:.7g}, {b:.7g}], [{c:.7g}, {d:.7g}]]", "Stored as four little-endian float32 values."]))
    elif kind == 11 and declared >= 30 and valid_length:
        count = struct.unpack_from("<I", payload)[0]
        anchor_x, anchor_y = struct.unpack_from("<ff", payload, 4)
        node.label = f"Cell #{number} — Vector text path (type 11)"
        node.children.append(Node("Path anchor (observed)", payload_start + 4, payload_start + 12,
                                  [f"x={anchor_x:.7g}, y={anchor_y:.7g}"]))
        expected = 30 + count * 12
        if expected == declared:
            commands = Node(f"Path commands ({count})", payload_start + 30, end,
                            ["Each entry is float32 X, float32 Y, uint32 path code."])
            for index in range(count):
                at = payload_start + 30 + index * 12
                x, y, code = struct.unpack_from("<ffI", data, at)
                base = code & 7
                names = {0: "move", 1: "line", 2: "cubic control", 3: "cubic point"}
                close = ", closes subpath" if code & 0x80 else ""
                commands.children.append(Node(f"Glyph/path point #{index + 1}: {names.get(base, 'unknown')}" + close,
                                              at, at + 12, [f"x={x:.7g}, y={y:.7g}, code=0x{code:08X}"]))
            node.children.append(commands)
        else:
            node.details.append(f"Path command count {count} does not fit the declared payload ({expected:,} expected); command list left raw.")
    elif kind == 10 and valid_length:
        streams = find_qoi_streams(payload)
        node.label = f"Cell #{number} — Inline resource (type 10)"
        for stream in streams:
            if stream.offset == 0 and stream.end_offset == len(payload):
                node.children.append(Node("QOI image", payload_start, end, [
                    f"{stream.width} × {stream.height}, {stream.channels} channels, colorspace {stream.colorspace}",
                    f"Encoded length: {stream.encoded_length:,} bytes",
                ]))
    elif kind in (25, 26):
        node.label = f"Cell #{number} — {'Linked image' if kind == 25 else 'Inline image link'} (type {kind})"
        strings = _strings(payload)
        if strings:
            node.children.append(Node("Embedded printable strings (uninterpreted)", payload_start, end, strings))
    elif kind == 14:
        node.label = f"Cell #{number} — Settings / text-like data (type 14)"
        strings = _strings(payload)
        if strings:
            node.children.append(Node("Embedded printable strings (uninterpreted)", payload_start, end, strings))
    return node


def parse_cdoc(data: bytes) -> Node:
    """Build a sequential tree of marker-framed records and all unframed gaps."""
    root = Node("CDOC", 0, len(data), [f"Size: {len(data):,} bytes", f"SHA-256: {sha256(data)}"])
    markers: list[int] = []
    cursor = 0
    while (found := data.find(MARKER, cursor)) >= 0:
        markers.append(found)
        cursor = found + len(MARKER)
    prior = 0
    for index, start in enumerate(markers, 1):
        if start > prior:
            root.children.append(Node(f"[Not Understood #{index:04d}: unframed bytes]", prior, start,
                                      [f"{start - prior:,} bytes before the next record marker."]))
        next_marker = markers[index] if index < len(markers) else -1
        record = _node_for_record(data, index, start, next_marker)
        root.children.append(record)
        prior = max(prior, record.end)
    if prior < len(data):
        root.children.append(Node(f"[Not Understood #{len(markers) + 1:04d}: trailing bytes]", prior, len(data),
                                  [f"{len(data) - prior:,} trailing bytes."]))
    return root


def parse_group_view(data: bytes) -> Node:
    """Derive a nesting view from type-3/type-4 records with matching headers.

    This is deliberately a visualization of the observed delimiter convention,
    not a claim that it is a complete CDOC grammar.  A close only closes the
    current group when both its scope and record ID agree with that opener.
    """
    source = parse_cdoc(data)
    root = Node(
        "CDOC — type-3/type-4 group view",
        0,
        len(data),
        ["Derived nesting view: type 3 opens a group; a matching type 4 closes it.",
         "A pair must have the same scope and record ID. Unmatched records remain explicit."],
    )
    stack: list[tuple[Node, int, int, str]] = [(root, -1, -1, "CDOC")]
    for cell in source.children:
        if cell.start + HEADER_SIZE > len(data) or data[cell.start : cell.start + 4] != MARKER:
            stack[-1][0].children.append(cell)
            continue
        scope, kind, _declared, record_id, _auxiliary = struct.unpack_from("<IIIII", data, cell.start + 4)
        number_match = re.search(r"Cell #(\d+)", cell.label)
        number = number_match.group(1) if number_match else "?"
        if kind == 3:
            group = Node(
                f"Cell #{number} — Group open (scope {scope}, record ID {record_id})",
                cell.start,
                cell.end,
                cell.details + ["Opening delimiter in the derived group view."],
            )
            stack[-1][0].children.append(group)
            stack.append((group, scope, record_id, number))
        elif kind == 4:
            close = Node(
                f"Cell #{number} — Group close (scope {scope}, record ID {record_id})",
                cell.start,
                cell.end,
                cell.details + ["Closing delimiter in the derived group view."],
            )
            if len(stack) > 1 and stack[-1][1:3] == (scope, record_id):
                stack[-1][0].children.append(close)
                stack.pop()
            else:
                close.label = f"[Not Understood: unmatched close] {close.label}"
                close.details.append("It does not match the currently open group, so it was not used to change nesting.")
                stack[-1][0].children.append(close)
        else:
            stack[-1][0].children.append(cell)
    for group, scope, record_id, number in stack[1:]:
        group.label = f"[Not Understood: unclosed] {group.label}"
        group.details.append("No matching type-4 close was found before the end of CDOC.")
    return root


def hexdump(data: bytes, start: int, end: int) -> str:
    """Return offset-aligned hexadecimal and ASCII columns for the selected span."""
    # Preserve 16-byte alignment around the selection, but avoid loading a huge QOI at once.
    view_start = start & ~0xF
    view_end = min(len(data), max(end, start + 1) + 0x100)
    view_end = min(len(data), (view_end + 15) & ~0xF)
    if end - start > 0x1000:
        view_end = min(len(data), view_start + 0x1100)
    lines = ["OFFSET    00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F  ASCII"]
    for at in range(view_start, view_end, 16):
        chunk = data[at : at + 16]
        hexes = " ".join(f"{byte:02X}" for byte in chunk).ljust(47)
        ascii_text = "".join(chr(byte) if 32 <= byte < 127 else "." for byte in chunk)
        lines.append(f"{at:08X}  {hexes}  {ascii_text}")
    if view_end < end:
        lines.append(f"… hex preview limited; selection is {end - start:,} bytes.")
    return "\n".join(lines)


def render_hexdump(widget: tk.Text, data: bytes, start: int, end: int) -> None:
    """Render an aligned dump, marking the selected byte range in blue.

    The text widget needs byte-level tags rather than a single formatted string:
    a selected cell can start or end in the middle of a 16-byte line.
    """
    view_start = start & ~0xF
    view_end = min(len(data), max(end, start + 1) + 0x100)
    view_end = min(len(data), (view_end + 15) & ~0xF)
    limited = end - start > 0x1000
    if limited:
        view_end = min(len(data), view_start + 0x1100)
    widget.tag_configure("selected_byte", foreground="#0066CC")
    widget.tag_configure("selected_offset", foreground="#0066CC")
    widget.insert("end", "OFFSET    00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F  ASCII\n")
    for at in range(view_start, view_end, 16):
        chunk = data[at : at + 16]
        intersects = at < end and at + len(chunk) > start
        widget.insert("end", f"{at:08X}", "selected_offset" if intersects else ())
        widget.insert("end", "  ")
        for index in range(16):
            if index < len(chunk):
                byte_at = at + index
                tag = "selected_byte" if start <= byte_at < end else ()
                widget.insert("end", f"{chunk[index]:02X}", tag)
            else:
                widget.insert("end", "  ")
            if index != 15:
                widget.insert("end", " ")
        widget.insert("end", "  ")
        for index, byte in enumerate(chunk):
            tag = "selected_byte" if start <= at + index < end else ()
            widget.insert("end", chr(byte) if 32 <= byte < 127 else ".", tag)
        widget.insert("end", "\n")
    if limited:
        widget.insert("end", f"… hex preview limited; selection is {end - start:,} bytes.\n")


class Inspector(ttk.Frame):
    def __init__(self, master: tk.Tk, path: Path):
        super().__init__(master)
        self.master = master
        self.data = b""
        self.current_path: Path | None = None
        self.items: dict[tuple[str, str], Node] = {}
        self.pack(fill="both", expand=True)
        self._build()
        self.open(path)

    def _build(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=6, pady=6)
        ttk.Button(toolbar, text="Open LDS…", command=self.choose_file).pack(side="left")
        self.path_label = ttk.Label(toolbar, text="", cursor="hand2")
        self.path_label.pack(side="left", padx=10)
        self.path_label.bind("<Button-1>", self.copy_path)
        self.copy_status = ttk.Label(toolbar, text="")
        self.copy_status.pack(side="left")
        split = ttk.Panedwindow(self, orient="horizontal")
        split.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(split)
        right = ttk.Frame(split)
        split.add(left, weight=1)
        split.add(right, weight=2)
        notebook = ttk.Notebook(left)
        notebook.pack(fill="both", expand=True)
        self.cells_tree = self._add_tree_tab(notebook, "Cells")
        self.groups_tree = self._add_tree_tab(notebook, "Groups (3 ↔ 4)")
        right_split = ttk.Panedwindow(right, orient="vertical")
        right_split.pack(fill="both", expand=True)
        detail_frame = ttk.Frame(right_split)
        hex_frame = ttk.Frame(right_split)
        right_split.add(detail_frame, weight=1)
        right_split.add(hex_frame, weight=3)
        self.details = tk.Text(detail_frame, height=7, wrap="word", state="disabled", font="TkDefaultFont")
        self.details.pack(fill="both", expand=True)
        self.hex = tk.Text(hex_frame, wrap="none", state="disabled", font=("Consolas", 10))
        yscroll = ttk.Scrollbar(hex_frame, orient="vertical", command=self.hex.yview)
        xscroll = ttk.Scrollbar(hex_frame, orient="horizontal", command=self.hex.xview)
        self.hex.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.hex.pack(side="top", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")

    def _add_tree_tab(self, notebook: ttk.Notebook, title: str) -> ttk.Treeview:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        tree = ttk.Treeview(frame, show="tree", selectmode="browse")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        tree.bind("<<TreeviewSelect>>", self.select)
        return tree

    def choose_file(self) -> None:
        filename = filedialog.askopenfilename(title="Open LDS file", filetypes=[("LDS files", "*.lds"), ("All files", "*.*")])
        if filename:
            self.open(Path(filename))

    def copy_path(self, _event: object = None) -> None:
        """Copy the currently inspected LDS filename to the system clipboard."""
        if self.current_path is None:
            return
        self.master.clipboard_clear()
        self.master.clipboard_append(str(self.current_path))
        self.master.update()
        self.copy_status.configure(text="Copied")
        self.master.after(1500, lambda: self.copy_status.configure(text=""))

    def open(self, path: Path) -> None:
        try:
            with zipfile.ZipFile(path) as archive:
                self.data = archive.read("CDOC")
                members = archive.infolist()
        except (OSError, KeyError, zipfile.BadZipFile) as error:
            messagebox.showerror("Cannot open LDS", str(error), parent=self.master)
            return
        self.master.title(f"xlds — {path.name}")
        self.current_path = path
        self.path_label.configure(text=str(path))
        self.copy_status.configure(text="")
        self.cells_tree.delete(*self.cells_tree.get_children())
        self.groups_tree.delete(*self.groups_tree.get_children())
        self.items.clear()
        root = Node(path.name, 0, len(self.data), ["LDS is a ZIP archive."])
        root.children.append(parse_cdoc(self.data))
        root.children.extend(Node(f"ZIP member: {info.filename}", 0, 0, [f"Compressed: {info.compress_size:,} bytes", f"Uncompressed: {info.file_size:,} bytes"])
                             for info in members if info.filename != "CDOC")
        item = self._insert(self.cells_tree, "", root)
        self.cells_tree.item(item, open=True)
        cdoc_item = self.cells_tree.get_children(item)[0]
        self.cells_tree.item(cdoc_item, open=True)
        self.cells_tree.selection_set(cdoc_item)
        group_item = self._insert(self.groups_tree, "", parse_group_view(self.data))
        self.groups_tree.item(group_item, open=True)

    def _insert(self, tree: ttk.Treeview, parent: str, node: Node) -> str:
        item = tree.insert(parent, "end", text=node.label)
        self.items[(str(tree), item)] = node
        for child in node.children:
            self._insert(tree, item, child)
        return item

    def select(self, _event: object = None) -> None:
        tree = _event.widget if _event is not None else self.cells_tree
        chosen = tree.selection()
        if not chosen:
            return
        node = self.items[(str(tree), chosen[0])]
        details = "\n".join(node.details or ["No confirmed interpretation for this selection."])
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", details)
        self.details.configure(state="disabled")
        self.hex.configure(state="normal")
        self.hex.delete("1.0", "end")
        if node.end > node.start:
            render_hexdump(self.hex, self.data, node.start, node.end)
        else:
            self.hex.insert("1.0", "This ZIP member has no CDOC byte range.")
        self.hex.configure(state="disabled")


def main() -> None:
    parser = argparse.ArgumentParser(description="Open a read-only graphical inspector for an LDS file.")
    parser.add_argument("path", nargs="?", type=Path, help="LDS file to inspect; omit to choose in the window")
    args = parser.parse_args()
    root = tk.Tk()
    root.minsize(900, 600)
    if args.path is None:
        filename = filedialog.askopenfilename(title="Open LDS file", filetypes=[("LDS files", "*.lds"), ("All files", "*.*")])
        if not filename:
            root.destroy()
            return
        args.path = Path(filename)
    Inspector(root, args.path)
    root.mainloop()


if __name__ == "__main__":
    main()
