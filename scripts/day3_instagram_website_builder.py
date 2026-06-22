"""
Day 3 - Autogrind
Instagram to Website Builder
------------------------------
Scrapes an Instagram profile via Apify, then uses Claude (claude-opus-4-8)
with streaming + tool use to generate a complete multi-file website:
  output/instagram_website/index.html
  output/instagram_website/style.css
  output/instagram_website/script.js

Score: 9.1 | Demand: 9 | Buildability: 8 | Value: 10

Usage:
  APIFY_API_KEY=... ANTHROPIC_API_KEY=... python day3_instagram_website_builder.py
  DEMO=1 ANTHROPIC_API_KEY=...              python day3_instagram_website_builder.py
"""

import anthropic
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
APIFY_API_KEY  = os.environ.get("APIFY_API_KEY", "")
ANTHROPIC_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
INSTAGRAM_USER = "anushka_karmakar._"
APIFY_ACTOR_ID = "apify~instagram-profile-scraper"
OUTPUT_DIR     = os.path.join(os.path.dirname(__file__), "..", "output", "instagram_website")
MAX_POSTS      = 12


# ── Apify scraping ────────────────────────────────────────────────────────────

def _http(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} from {url}: {e.read().decode()[:300]}")


def scrape_instagram_profile(username):
    if not APIFY_API_KEY:
        raise RuntimeError("APIFY_API_KEY not set. Use DEMO=1 to skip scraping.")

    print(f"[apify] Scraping @{username} …")
    token = APIFY_API_KEY
    run = _http(
        "POST",
        f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs?token={token}",
        data=json.dumps({"usernames": [username], "resultsType": "details", "resultsLimit": MAX_POSTS}).encode(),
        headers={"Content-Type": "application/json"},
    )
    run_id = run["data"]["id"]
    print(f"[apify] Run {run_id} started …")

    for _ in range(60):
        time.sleep(5)
        status = _http("GET", f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs/{run_id}?token={token}")
        s = status["data"]["status"]
        print(f"[apify] status={s}")
        if s in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break

    if s != "SUCCEEDED":
        raise RuntimeError(f"Apify run ended with status={s}")

    dataset_id = status["data"]["defaultDatasetId"]
    items = _http("GET", f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={token}")
    if not items:
        raise RuntimeError("Apify returned no items")

    profile = items[0] if isinstance(items, list) else items.get("data", {}).get("items", [{}])[0]
    print(f"[apify] Scraped: {profile.get('fullName', username)}, {profile.get('followersCount', '?')} followers")
    return profile


# ── Demo data ─────────────────────────────────────────────────────────────────

DEMO_PROFILE = {
    "username": "anushka_karmakar._",
    "fullName": "Anushka Karmakar",
    "biography": "dancer 🌸 | choreographer | spreading joy one move at a time\ncollabs → DM",
    "followersCount": 48700,
    "followingCount": 812,
    "postsCount": 234,
    "profilePicUrl": "https://picsum.photos/seed/anushka/200/200",
    "externalUrl": "",
    "latestPosts": [
        {"shortCode": f"d{i}", "displayUrl": f"https://picsum.photos/seed/post{i}/600/600",
         "caption": cap, "likesCount": likes}
        for i, (cap, likes) in enumerate([
            ("Practice makes perfect ✨ new routine dropping soon", 3210),
            ("Behind the scenes of our latest collab 🎬", 2870),
            ("Workshop day! So grateful for everyone who showed up 💜", 4120),
            ("When the music hits different 🎵", 5640),
            ("Golden hour vibes 🌅", 3980),
            ("Bringing the energy every single day 🔥", 4450),
            ("Thank you for 40K! This community means everything 🙏", 7200),
            ("New month, new moves, same passion", 2910),
            ("Studio sessions ❤️‍🔥", 3340),
            ("Every day is an opportunity to get better", 2780),
            ("Rehearsals for the big show 🎭", 3650),
            ("Dance is the hidden language of the soul 💫", 4890),
        ], 1)
    ],
}


# ── Claude website generation (streaming + tool use) ─────────────────────────

SAVE_FILE_TOOL = {
    "name": "save_file",
    "description": (
        "Save a website file to disk. Call this once per file. "
        "Generate all three files: index.html, style.css, script.js."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "enum": ["index.html", "style.css", "script.js"],
                "description": "The filename to save.",
            },
            "content": {
                "type": "string",
                "description": "Full file content.",
            },
        },
        "required": ["filename", "content"],
    },
}


def build_prompt(profile):
    posts = profile.get("latestPosts") or profile.get("posts") or []
    posts_json = json.dumps(
        [{"caption": p.get("caption", ""), "imageUrl": p.get("displayUrl", ""),
          "likes": p.get("likesCount", 0), "url": f"https://www.instagram.com/p/{p.get('shortCode','')}/"}
         for p in posts[:MAX_POSTS]],
        indent=2,
    )
    ig_url = f"https://www.instagram.com/{profile.get('username', INSTAGRAM_USER)}/"
    return f"""You are a world-class web designer. Build a stunning, production-ready portfolio website for this Instagram creator.

## Profile Data
- Name: {profile.get('fullName', profile.get('username', ''))}
- Handle: @{profile.get('username', '')}
- Bio: {profile.get('biography', '')}
- Followers: {profile.get('followersCount', 0):,}
- Following: {profile.get('followingCount', 0):,}
- Posts: {profile.get('postsCount', 0):,}
- Avatar: {profile.get('profilePicUrl', '')}
- Instagram URL: {ig_url}
- External link: {profile.get('externalUrl', '')}

## Latest Posts (JSON)
{posts_json}

## Requirements
Generate THREE files by calling `save_file` three times:

### 1. index.html
- Semantic HTML5, references style.css and script.js
- Sections: hero (avatar, name, handle, stats, CTA), about (rewrite bio as warm first-person paragraphs), gallery (all {len(posts[:MAX_POSTS])} posts as clickable cards with real image URLs), footer
- No inline styles, no inline JS

### 2. style.css
- Dark aesthetic (#0e0e0e background, #e040fb accent)
- Mobile-first responsive (grid for gallery, flexbox for hero)
- Smooth hover animations on cards
- Google Fonts import (Inter or Poppins)
- CSS custom properties (variables)

### 3. script.js
- Lazy-load gallery images with IntersectionObserver
- Lightbox: clicking a card shows full image overlay with caption and like count
- Keyboard nav for lightbox (Esc / arrow keys)
- Animate stats counters on scroll (followers, following, posts)
- No external libraries — vanilla JS only

Call `save_file` exactly three times (index.html, style.css, script.js). Make the website impressive."""


def generate_website_with_claude(profile):
    if not ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Cannot call Claude.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    saved_files = {}

    messages = [{"role": "user", "content": build_prompt(profile)}]

    print("[claude] Generating website with claude-opus-4-8 (streaming) …")

    while True:
        with client.messages.stream(
            model="claude-opus-4-8",
            max_tokens=16000,
            thinking={"type": "adaptive"},
            tools=[SAVE_FILE_TOOL],
            messages=messages,
        ) as stream:
            # Show thinking/text output live
            for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "thinking":
                        print("\n[thinking…]", flush=True)
                    elif event.content_block.type == "text":
                        print("", flush=True)
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        print(event.delta.text, end="", flush=True)

            response = stream.get_final_message()

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use" and block.name == "save_file":
                    filename = block.input["filename"]
                    content  = block.input["content"]
                    path = os.path.join(OUTPUT_DIR, filename)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                    saved_files[filename] = path
                    print(f"\n[saved] {filename} ({len(content):,} chars)")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Saved {filename} successfully.",
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            # end_turn or max_tokens — done
            break

    return saved_files


# ── Static fallback (no API key needed) ──────────────────────────────────────

def _e(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def generate_website_static(profile):
    """Generate index.html + style.css + script.js without Claude."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    posts   = (profile.get("latestPosts") or profile.get("posts") or [])[:MAX_POSTS]
    name    = _e(profile.get("fullName") or profile.get("username", INSTAGRAM_USER))
    handle  = _e(profile.get("username", INSTAGRAM_USER))
    bio     = _e(profile.get("biography", ""))
    avatar  = _e(profile.get("profilePicUrl") or profile.get("profilePicUrlHD") or "")
    ig_url  = f"https://www.instagram.com/{profile.get('username', INSTAGRAM_USER)}/"
    ext_url = profile.get("externalUrl", "")
    followers = profile.get("followersCount", 0)
    following = profile.get("followingCount", 0)
    n_posts   = profile.get("postsCount", 0)
    year      = datetime.now().year

    gallery_items = ""
    for p in posts:
        sc   = p.get("shortCode", "")
        img  = _e(p.get("displayUrl") or p.get("thumbnailUrl") or "")
        cap  = _e((p.get("caption") or "")[:140])
        likes = p.get("likesCount", 0)
        purl = f"https://www.instagram.com/p/{sc}/" if sc else ig_url
        gallery_items += f"""
    <div class="card" data-img="{img}" data-caption="{cap}" data-likes="{likes:,}">
      <a class="card-link" href="{_e(purl)}" target="_blank" rel="noopener">
        <img src="{img}" alt="Post" loading="lazy" onerror="this.parentElement.parentElement.style.display='none'">
        <div class="card-overlay"><span>&#9829; {likes:,}</span></div>
      </a>
      <p class="card-caption">{cap}</p>
    </div>"""

    ext_btn = (f'<a class="btn btn-outline" href="{_e(ext_url)}" target="_blank" rel="noopener">Website ↗</a>'
               if ext_url else "")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} | Portfolio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
</head>
<body>

  <header class="hero">
    {"<img class='avatar' src='" + avatar + "' alt='Avatar'>" if avatar else ""}
    <h1 class="hero-name">{name}</h1>
    <p class="hero-handle">@{handle}</p>
    <div class="stats">
      <div class="stat"><span class="stat-num" data-target="{followers}">{followers:,}</span><span class="stat-lbl">Followers</span></div>
      <div class="stat"><span class="stat-num" data-target="{following}">{following:,}</span><span class="stat-lbl">Following</span></div>
      <div class="stat"><span class="stat-num" data-target="{n_posts}">{n_posts:,}</span><span class="stat-lbl">Posts</span></div>
    </div>
    <div class="cta-row">
      <a class="btn btn-primary" href="{_e(ig_url)}" target="_blank" rel="noopener">Follow on Instagram</a>
      {ext_btn}
    </div>
  </header>

  <section class="about">
    <h2>About</h2>
    <p>{bio.replace('&#xa;','<br>').replace(chr(10),'<br>')}</p>
  </section>

  <section class="gallery-section">
    <h2>Latest Posts</h2>
    <div class="gallery">
{gallery_items}
    </div>
  </section>

  <div class="lightbox" id="lightbox" role="dialog" aria-modal="true" aria-label="Image viewer" hidden>
    <button class="lb-close" id="lb-close" aria-label="Close">&#10005;</button>
    <button class="lb-prev"  id="lb-prev"  aria-label="Previous">&#8592;</button>
    <button class="lb-next"  id="lb-next"  aria-label="Next">&#8594;</button>
    <div class="lb-content">
      <img id="lb-img" src="" alt="">
      <p id="lb-caption"></p>
      <p id="lb-likes"></p>
    </div>
  </div>

  <footer>
    <p>&copy; {year} {name} &mdash; <a href="{_e(ig_url)}">@{handle}</a> &mdash; Built with Autogrind</p>
  </footer>

  <script src="script.js"></script>
</body>
</html>
"""

    css = """/* ── Reset & Variables ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:      #0e0e0e;
  --surface: #1a1a1a;
  --accent:  #e040fb;
  --text:    #f0f0f0;
  --muted:   #888;
  --radius:  12px;
  --font:    'Inter', system-ui, sans-serif;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
  line-height: 1.6;
}

/* ── Hero ── */
.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 64px 24px 48px;
  background: linear-gradient(160deg, #1a0026 0%, #0e0e0e 65%);
}

.avatar {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  border: 3px solid var(--accent);
  object-fit: cover;
  margin-bottom: 20px;
  transition: transform .3s;
}
.avatar:hover { transform: scale(1.05); }

.hero-name   { font-size: 2.4rem; font-weight: 700; }
.hero-handle { color: var(--accent); font-size: 1rem; margin: 4px 0 20px; }

/* ── Stats ── */
.stats {
  display: flex;
  gap: 40px;
  margin: 0 0 28px;
}
.stat { text-align: center; }
.stat-num {
  display: block;
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1;
}
.stat-lbl {
  font-size: 0.75rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* ── CTA buttons ── */
.cta-row { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; }
.btn {
  padding: 11px 28px;
  border-radius: 99px;
  font-size: 0.9rem;
  font-weight: 600;
  text-decoration: none;
  transition: opacity .2s, transform .15s;
  cursor: pointer;
}
.btn:hover { opacity: .85; transform: translateY(-1px); }
.btn-primary { background: var(--accent); color: #fff; border: none; }
.btn-outline  { border: 1.5px solid var(--accent); color: var(--accent); background: transparent; }

/* ── About ── */
.about {
  max-width: 680px;
  margin: 0 auto;
  padding: 56px 24px;
}
.about h2, .gallery-section h2 {
  font-size: 1.6rem;
  color: var(--accent);
  margin-bottom: 16px;
}
.about p { color: #ccc; }

/* ── Gallery ── */
.gallery-section {
  padding: 40px 24px 72px;
  background: var(--surface);
}
.gallery-section h2 { text-align: center; margin-bottom: 32px; }
.gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 20px;
  max-width: 1100px;
  margin: 0 auto;
}
.card {
  background: var(--bg);
  border-radius: var(--radius);
  overflow: hidden;
  cursor: pointer;
  transition: transform .25s, box-shadow .25s;
  opacity: 0;
  transform: translateY(20px);
  transition: opacity .5s, transform .5s;
}
.card.visible {
  opacity: 1;
  transform: translateY(0);
}
.card:hover { transform: translateY(-4px); box-shadow: 0 8px 32px rgba(224,64,251,.2); }

.card-link { display: block; position: relative; aspect-ratio: 1; overflow: hidden; }
.card-link img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform .4s; }
.card:hover .card-link img { transform: scale(1.05); }

.card-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,.45);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity .3s;
  font-size: 1.1rem;
  font-weight: 600;
}
.card:hover .card-overlay { opacity: 1; }

.card-caption {
  padding: 10px 14px;
  font-size: .82rem;
  color: #bbb;
  min-height: 38px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ── Lightbox ── */
.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.92);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.lightbox[hidden] { display: none; }

.lb-content {
  max-width: min(90vw, 700px);
  text-align: center;
}
.lb-content img {
  max-width: 100%;
  max-height: 70vh;
  border-radius: var(--radius);
  object-fit: contain;
}
#lb-caption { color: #ddd; margin-top: 12px; font-size: .9rem; }
#lb-likes   { color: var(--accent); margin-top: 6px; font-size: .85rem; }

.lb-close, .lb-prev, .lb-next {
  position: fixed;
  background: rgba(255,255,255,.1);
  border: none;
  color: #fff;
  cursor: pointer;
  border-radius: 50%;
  width: 44px;
  height: 44px;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background .2s;
}
.lb-close:hover, .lb-prev:hover, .lb-next:hover { background: rgba(255,255,255,.2); }
.lb-close { top: 20px; right: 20px; }
.lb-prev  { left: 12px; top: 50%; transform: translateY(-50%); }
.lb-next  { right: 12px; top: 50%; transform: translateY(-50%); }

/* ── Footer ── */
footer {
  text-align: center;
  padding: 24px;
  font-size: .8rem;
  color: var(--muted);
}
footer a { color: var(--accent); text-decoration: none; }

/* ── Responsive ── */
@media (max-width: 520px) {
  .hero-name { font-size: 1.7rem; }
  .stats     { gap: 20px; }
  .lb-prev   { left: 4px; }
  .lb-next   { right: 4px; }
}
"""

    js = """// ── Lazy load gallery cards ──────────────────────────────────────────────────
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add('visible');
      observer.unobserve(e.target);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.card').forEach(c => observer.observe(c));


// ── Animated stat counters ────────────────────────────────────────────────────
function animateCounter(el) {
  const target = parseInt(el.dataset.target, 10);
  const duration = 1400;
  const start = performance.now();
  (function step(now) {
    const t = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(ease * target).toLocaleString();
    if (t < 1) requestAnimationFrame(step);
  })(start);
}

const statsObserver = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.querySelectorAll('.stat-num').forEach(animateCounter);
      statsObserver.unobserve(e.target);
    }
  });
}, { threshold: 0.5 });

const statsEl = document.querySelector('.stats');
if (statsEl) statsObserver.observe(statsEl);


// ── Lightbox ──────────────────────────────────────────────────────────────────
const lb       = document.getElementById('lightbox');
const lbImg    = document.getElementById('lb-img');
const lbCap    = document.getElementById('lb-caption');
const lbLikes  = document.getElementById('lb-likes');
const lbClose  = document.getElementById('lb-close');
const lbPrev   = document.getElementById('lb-prev');
const lbNext   = document.getElementById('lb-next');

const cards = Array.from(document.querySelectorAll('.card'));
let current = 0;

function openLightbox(idx) {
  current = idx;
  const card = cards[idx];
  lbImg.src       = card.dataset.img;
  lbCap.textContent   = card.dataset.caption;
  lbLikes.textContent = '♥ ' + card.dataset.likes;
  lb.hidden = false;
  document.body.style.overflow = 'hidden';
  lbClose.focus();
}

function closeLightbox() {
  lb.hidden = true;
  document.body.style.overflow = '';
}

cards.forEach((card, idx) => {
  card.addEventListener('click', (e) => {
    // Don't intercept the Instagram link click
    if (e.target.closest('a.card-link')) return;
    openLightbox(idx);
  });
  // Also open lightbox when clicking the image directly (prevent navigation)
  const link = card.querySelector('a.card-link');
  if (link) {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      openLightbox(idx);
    });
  }
});

lbClose.addEventListener('click', closeLightbox);
lb.addEventListener('click', (e) => { if (e.target === lb) closeLightbox(); });

lbPrev.addEventListener('click', () => openLightbox((current - 1 + cards.length) % cards.length));
lbNext.addEventListener('click', () => openLightbox((current + 1) % cards.length));

document.addEventListener('keydown', (e) => {
  if (lb.hidden) return;
  if (e.key === 'Escape')      closeLightbox();
  if (e.key === 'ArrowLeft')   openLightbox((current - 1 + cards.length) % cards.length);
  if (e.key === 'ArrowRight')  openLightbox((current + 1) % cards.length);
});
"""

    files = {
        "index.html": html,
        "style.css":  css,
        "script.js":  js,
    }
    saved = {}
    for fname, content in files.items():
        path = os.path.join(OUTPUT_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        saved[fname] = path
        print(f"[saved] {fname} ({len(content):,} chars)")
    return saved


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    demo = os.environ.get("DEMO", "").lower() in ("1", "true")

    # 1. Get profile data
    if demo:
        print("[mode] DEMO — using sample Instagram data")
        profile = DEMO_PROFILE
    else:
        profile = scrape_instagram_profile(INSTAGRAM_USER)

    # Save raw profile data
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "profile_data.json"), "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print("[saved] profile_data.json")

    # 2. Generate website: Claude if API key present, static fallback otherwise
    if ANTHROPIC_KEY:
        saved = generate_website_with_claude(profile)
    else:
        print("[build] No ANTHROPIC_API_KEY — generating static website (set key for Claude-enhanced output)")
        saved = generate_website_static(profile)

    print(f"\n{'='*60}")
    print(f"[done] {len(saved)} website files generated:")
    for fname, path in saved.items():
        size = os.path.getsize(path)
        print(f"  {fname:14s}  {size:>7,} bytes")
    print(f"{'='*60}")
    print(f"\nOpen: file://{os.path.abspath(os.path.join(OUTPUT_DIR, 'index.html'))}")


if __name__ == "__main__":
    main()
