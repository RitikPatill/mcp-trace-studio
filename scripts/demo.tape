# VHS tape — requires vhs v0.7+ (https://github.com/charmbracelet/vhs)
# Usage: vhs scripts/demo.tape
# Output: docs/demo.gif

Output docs/demo.gif

Set FontSize 13
Set Width 1200
Set Height 600
Set Theme "Dracula"

Type "# MCP Trace Studio — demo"
Enter
Sleep 500ms

Type "just demo"
Enter
Sleep 5s

Type "# Traces written to SQLite. Start services:"
Enter
Sleep 500ms

Type "# just backend   (Terminal 1)"
Enter
Sleep 300ms

Type "# just frontend  (Terminal 2)"
Enter
Sleep 300ms

Type "# Then open http://localhost:3000"
Enter
Sleep 2s
