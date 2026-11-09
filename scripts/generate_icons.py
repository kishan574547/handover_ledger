import os
from pathlib import Path
from PIL import Image, ImageDraw

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public"
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

# 1. Create clean SVG logo mark
svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <defs>
    <linearGradient id="hl-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1F3864" />
      <stop offset="100%" stop-color="#142544" />
    </linearGradient>
  </defs>
  <!-- Rounded Square Container in #1F3864 -->
  <rect x="4" y="4" width="92" height="92" rx="22" fill="url(#hl-bg)" />
  
  <!-- Shield Outline in White -->
  <path d="M50 16 L74 24 C74 48 58 68 50 78 C42 68 26 48 26 24 Z" 
        fill="none" 
        stroke="#FFFFFF" 
        stroke-width="5" 
        stroke-linecap="round" 
        stroke-linejoin="round" />
        
  <!-- Check Mark whose tail connects to 3 ledger lines -->
  <path d="M36 44 L45 53 L62 34" 
        fill="none" 
        stroke="#14B8A6" 
        stroke-width="5.5" 
        stroke-linecap="round" 
        stroke-linejoin="round" />
        
  <!-- 3 Horizontal Ledger Lines representing verifiable auditability -->
  <line x1="39" y1="62" x2="61" y2="62" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" />
  <line x1="43" y1="69" x2="57" y2="69" stroke="#94A3B8" stroke-width="2.5" stroke-linecap="round" />
  <line x1="47" y1="74" x2="53" y2="74" stroke="#64748B" stroke-width="2" stroke-linecap="round" />
</svg>
'''

svg_path = PUBLIC_DIR / "favicon.svg"
with open(svg_path, "w", encoding="utf-8") as f:
    f.write(svg_content)
print(f"Wrote {svg_path}")

# 2. Render PNG icons at various sizes using PIL
def draw_icon(size: int) -> Image.Image:
    scale = 4  # supersample for antialiasing
    img_size = size * scale
    img = Image.new("RGBA", (img_size, img_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = 4 * scale
    radius = 22 * scale
    # Background rounded rectangle in #1F3864
    bg_color = (31, 56, 100, 255)
    draw.rounded_rectangle(
        [pad, pad, img_size - pad, img_size - pad],
        radius=radius,
        fill=bg_color
    )

    # Shield points: (50, 16) -> (74, 24) -> (74, 48) -> (50, 78) -> (26, 48) -> (26, 24)
    # Using simple polygon with stroke
    shield_pts = [
        (50 * scale, 17 * scale),
        (73 * scale, 25 * scale),
        (73 * scale, 48 * scale),
        (50 * scale, 77 * scale),
        (27 * scale, 48 * scale),
        (27 * scale, 25 * scale),
    ]
    draw.polygon(shield_pts, fill=None, outline=(255, 255, 255, 255), width=int(5 * scale))

    # Checkmark in teal (20, 184, 166)
    check_pts = [
        (36 * scale, 44 * scale),
        (45 * scale, 53 * scale),
        (63 * scale, 34 * scale)
    ]
    draw.line(check_pts, fill=(20, 184, 166, 255), width=int(5.5 * scale), joint="curve")

    # Ledger lines
    draw.line([(39 * scale, 62 * scale), (61 * scale, 62 * scale)], fill=(255, 255, 255, 255), width=int(3 * scale))
    draw.line([(43 * scale, 69 * scale), (57 * scale, 69 * scale)], fill=(148, 163, 184, 255), width=int(2.5 * scale))
    draw.line([(47 * scale, 74 * scale), (53 * scale, 74 * scale)], fill=(100, 116, 139, 255), width=int(2 * scale))

    return img.resize((size, size), Image.Resampling.LANCZOS)

for sz, filename in [
    (32, "favicon-32.png"),
    (180, "apple-touch-icon.png"),
    (192, "icon-192.png"),
    (512, "icon-512.png")
]:
    out_img = draw_icon(sz)
    out_path = PUBLIC_DIR / filename
    out_img.save(out_path, "PNG")
    print(f"Generated {out_path} ({sz}x{sz})")

# 3. Create site.webmanifest
manifest_content = '''{
  "name": "HandoverLedger",
  "short_name": "HandoverLedger",
  "icons": [
    {
      "src": "/icon-192.png",
      "type": "image/png",
      "sizes": "192x192"
    },
    {
      "src": "/icon-512.png",
      "type": "image/png",
      "sizes": "512x512"
    }
  ],
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#1F3864",
  "background_color": "#F8FAFC"
}
'''
with open(PUBLIC_DIR / "site.webmanifest", "w", encoding="utf-8") as f:
    f.write(manifest_content)
print("Generated site.webmanifest")
