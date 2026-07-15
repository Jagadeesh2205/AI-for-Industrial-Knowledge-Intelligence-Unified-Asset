import re
import codecs

with codecs.open('frontend/src/index.css', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Fix the broken comments
content = content.replace('\"?\"?', '--').replace('\"?', '-')

root_css = '''/* -- CSS Custom Properties (Design Tokens) -- */
:root {
  --bg-void:        #0A0C0F;
  --bg-surface:     #111419;
  --bg-elevated:    #1A1F27;
  --border-steel:   #252B35;
  --text-primary:   #E8EBF0;
  --text-secondary: #6B7890;
  --accent-teal:    #00D4B8;
  --status-safe:    #22C55E;
  --status-warn:    #F59E0B;
  --status-critical:#EF4444;
  --status-neutral: #3B82F6;
  --terminal-green: #4ADE80;

  /* Typography */
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-display: 'Space Grotesk', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* Spacing */
  --sidebar-width: 260px;
  --sidebar-collapsed: 72px;
  --header-height: 64px;

  /* Radius */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;

  /* Transitions */
  --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 250ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 400ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* -- Global Reset & Base -- */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-sans);
  background: var(--bg-void);
  color: var(--text-primary);
  line-height: 1.5;
  min-height: 100vh;
}'''

# find the end of body tag and replace everything before it
body_end = content.find('}', content.find('body {')) + 1
if body_end > 0:
    content = root_css + content[body_end:]

with codecs.open('frontend/src/index.css', 'w', encoding='utf-8') as f:
    f.write(content)
