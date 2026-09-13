# lds-qoi-reverse-engeering

## LDS explorer

From this checkout in PowerShell, open an LDS file in the read-only inspector:

```powershell
.\xlds .\lds\glyph-ascii-01-punct-digits.lds
```

To use the bare `xlds FILE.lds` form from elsewhere, add this checkout to your
`PATH` (the included `xlds.cmd` launcher supplies the package path).

`xlds` shows the ZIP/CDOC structure in a tree at left.  The right-hand pane
shows an offset-aligned hex dump and only those field interpretations supported
by the current research.  Unknown spans are deliberately labelled
`[Not Understood #....]`; this is an explorer, not a claim of a complete LDS
file specification.
