"""
Day 3 - Autogrind
Instagram to Website Builder
------------------------------
Scrapes an Instagram profile via Apify, then generates a polished
static portfolio website (HTML + CSS) from the profile data.
Uses Claude to write engaging bio/about copy.

Score: 9.1 | Demand: 9 | Buildability: 8 | Value: 10
"""

import json
import os
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────
APIFY_API_KEY   = os.environ.get("APIFY_API_KEY", "")
ANTHROPIC_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
INSTAGRAM_USER  = "anushka_karmakar._"
APIFY_ACTOR_ID  = "apify~instagram-profile-scraper"   # official Apify Instagram profile actor
OUTPUT_DIR      = os.path.join(os.path.dirname(__file__), "..", "output", "instagram_website")
MAX_POSTS       = 12   # posts to show in the gallery


# ── HTTP helpers ─────────────────────────────────────────────────────────────

def _http(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} from {url}: {body[:400]}")


def apify_post(path, payload):
    url  = f"https://api.apify.com/v2{path}?token={APIFY_API_KEY}"
    data = json.dumps(payload).encode()
    return _http("POST", url, data=data, headers={"Content-Type": "application/json"})


def apify_get(path):
    url = f"https://api.apify.com/v2{path}?token={APIFY_API_KEY}"
    return _http("GET", url)


# ── Apify scraping ────────────────────────────────────────────────────────────

def scrape_instagram_profile(username):
    print(f"[apify] Starting Instagram scrape for @{username} …")

    # Start the actor run
    run_resp = apify_post(
        f"/acts/{APIFY_ACTOR_ID}/runs",
        {
            "usernames": [username],
            "resultsType": "details",
            "resultsLimit": MAX_POSTS,
        }
    )
    run_id = run_resp["data"]["id"]
    print(f"[apify] Run started: {run_id}")

    # Poll until finished
    for attempt in range(60):
        time.sleep(5)
        status_resp = apify_get(f"/acts/{APIFY_ACTOR_ID}/runs/{run_id}")
        status = status_resp["data"]["status"]
        print(f"[apify] status={status} ({attempt + 1}/60)")
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break

    if status != "SUCCEEDED":
        raise RuntimeError(f"Apify run did not succeed: status={status}")

    # Fetch results from the default dataset
    dataset_id = status_resp["data"]["defaultDatasetId"]
    items_resp  = apify_get(f"/datasets/{dataset_id}/items")
    items = items_resp if isinstance(items_resp, list) else items_resp.get("data", {}).get("items", [])

    if not items:
        raise RuntimeError("Apify returned no data for this profile.")

    profile = items[0]
    print(f"[apify] Got profile: {profile.get('fullName', username)} "
          f"({profile.get('followersCount', '?')} followers)")
    return profile


# ── Claude copy generation ────────────────────────────────────────────────────

def generate_about_copy(profile):
    if not ANTHROPIC_KEY:
        # Fall back to the raw bio
        return profile.get("biography", "")

    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    bio        = profile.get("biography", "")
    full_name  = profile.get("fullName", profile.get("username", ""))
    followers  = profile.get("followersCount", 0)
    posts_n    = profile.get("postsCount", 0)
    ext_url    = profile.get("externalUrl", "")

    prompt = (
        f"You are a copywriter creating an 'About Me' section for a portfolio website.\n"
        f"Instagram profile:\n"
        f"  Name: {full_name}\n"
        f"  Bio: {bio}\n"
        f"  Followers: {followers:,}\n"
        f"  Posts: {posts_n}\n"
        f"  External link: {ext_url}\n\n"
        f"Write 2-3 short, warm, first-person paragraphs for the About section. "
        f"Keep the original voice. No hashtags. No emojis unless they appear in the bio."
    )

    resp = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


# ── HTML generation ───────────────────────────────────────────────────────────

def _escape(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_gallery_items(posts):
    html_parts = []
    for post in posts[:MAX_POSTS]:
        img_src     = post.get("displayUrl") or post.get("thumbnailUrl") or ""
        caption     = _escape((post.get("caption") or "")[:120])
        likes       = post.get("likesCount", 0)
        short_code  = post.get("shortCode", "")
        post_url    = f"https://www.instagram.com/p/{short_code}/" if short_code else "#"
        html_parts.append(f"""
        <div class="card">
          <a href="{_escape(post_url)}" target="_blank" rel="noopener">
            <img src="{_escape(img_src)}" alt="Post" loading="lazy" onerror="this.style.display='none'">
          </a>
          <div class="card-body">
            <p class="caption">{caption}</p>
            <span class="likes">&#9829; {likes:,}</span>
          </div>
        </div>""")
    return "\n".join(html_parts)


def generate_website(profile, about_copy, posts):
    full_name   = _escape(profile.get("fullName") or profile.get("username", INSTAGRAM_USER))
    username    = _escape(profile.get("username", INSTAGRAM_USER))
    followers   = profile.get("followersCount", 0)
    following   = profile.get("followingCount", 0)
    posts_count = profile.get("postsCount", 0)
    avatar_url  = _escape(profile.get("profilePicUrlHD") or profile.get("profilePicUrl") or "")
    ext_url     = profile.get("externalUrl", "")
    ig_url      = f"https://www.instagram.com/{profile.get('username', INSTAGRAM_USER)}/"
    about_html  = _escape(about_copy).replace("&#xa;", "<br>").replace("\n", "<br>")
    gallery     = build_gallery_items(posts)
    year        = datetime.now().year

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{full_name} | Portfolio</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:      #0e0e0e;
      --surface: #1a1a1a;
      --accent:  #e040fb;
      --text:    #f0f0f0;
      --muted:   #888;
      --radius:  12px;
    }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Segoe UI', system-ui, sans-serif;
      line-height: 1.6;
    }}

    /* ── Hero ── */
    .hero {{
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding: 64px 24px 48px;
      background: linear-gradient(160deg, #1a0026 0%, #0e0e0e 60%);
    }}
    .avatar {{
      width: 120px; height: 120px;
      border-radius: 50%;
      border: 3px solid var(--accent);
      object-fit: cover;
      margin-bottom: 20px;
    }}
    .hero h1 {{ font-size: 2.2rem; font-weight: 700; }}
    .handle  {{ color: var(--accent); font-size: 1rem; margin: 4px 0 16px; }}

    .stats {{
      display: flex; gap: 32px;
      margin: 16px 0 24px;
    }}
    .stat {{ text-align: center; }}
    .stat strong {{ display: block; font-size: 1.4rem; }}
    .stat span   {{ font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }}

    .cta-row {{ display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; }}
    .btn {{
      padding: 10px 24px;
      border-radius: 24px;
      font-size: 0.9rem;
      font-weight: 600;
      text-decoration: none;
      transition: opacity .2s;
    }}
    .btn:hover {{ opacity: 0.85; }}
    .btn-primary {{ background: var(--accent); color: #fff; }}
    .btn-outline {{ border: 1.5px solid var(--accent); color: var(--accent); }}

    /* ── About ── */
    .about {{
      max-width: 680px; margin: 0 auto; padding: 56px 24px;
    }}
    .about h2 {{ font-size: 1.5rem; margin-bottom: 16px; color: var(--accent); }}
    .about p  {{ color: #ccc; margin-bottom: 12px; }}

    /* ── Gallery ── */
    .gallery-section {{
      padding: 40px 24px 64px;
      background: var(--surface);
    }}
    .gallery-section h2 {{
      text-align: center;
      font-size: 1.5rem;
      margin-bottom: 32px;
      color: var(--accent);
    }}
    .gallery {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 20px;
      max-width: 1100px;
      margin: 0 auto;
    }}
    .card {{
      background: var(--bg);
      border-radius: var(--radius);
      overflow: hidden;
      transition: transform .2s;
    }}
    .card:hover {{ transform: translateY(-4px); }}
    .card img {{
      width: 100%; aspect-ratio: 1;
      object-fit: cover;
      display: block;
    }}
    .card-body {{ padding: 12px 14px; }}
    .caption {{ font-size: 0.85rem; color: #bbb; margin-bottom: 8px; min-height: 36px; }}
    .likes {{ font-size: 0.8rem; color: var(--muted); }}

    /* ── Footer ── */
    footer {{
      text-align: center;
      padding: 24px;
      font-size: 0.8rem;
      color: var(--muted);
    }}
    footer a {{ color: var(--accent); text-decoration: none; }}

    @media (max-width: 480px) {{
      .hero h1 {{ font-size: 1.6rem; }}
      .stats  {{ gap: 20px; }}
    }}
  </style>
</head>
<body>

  <!-- Hero -->
  <section class="hero">
    {"<img class='avatar' src='" + avatar_url + "' alt='Profile photo'>" if avatar_url else ""}
    <h1>{full_name}</h1>
    <p class="handle">@{username}</p>

    <div class="stats">
      <div class="stat"><strong>{followers:,}</strong><span>Followers</span></div>
      <div class="stat"><strong>{following:,}</strong><span>Following</span></div>
      <div class="stat"><strong>{posts_count:,}</strong><span>Posts</span></div>
    </div>

    <div class="cta-row">
      <a class="btn btn-primary" href="{_escape(ig_url)}" target="_blank" rel="noopener">
        Follow on Instagram
      </a>
      {"<a class='btn btn-outline' href='" + _escape(ext_url) + "' target='_blank' rel='noopener'>Visit Website</a>" if ext_url else ""}
    </div>
  </section>

  <!-- About -->
  <section class="about">
    <h2>About</h2>
    <p>{about_html}</p>
  </section>

  <!-- Gallery -->
  <section class="gallery-section">
    <h2>Latest Posts</h2>
    <div class="gallery">
{gallery}
    </div>
  </section>

  <!-- Footer -->
  <footer>
    <p>
      &copy; {year} {full_name} &mdash;
      <a href="{_escape(ig_url)}" target="_blank" rel="noopener">@{username}</a>
      &nbsp;|&nbsp; Built with Autogrind &times; Instagram to Website
    </p>
  </footer>

</body>
</html>
"""


# ── Demo / offline mode ───────────────────────────────────────────────────────

DEMO_PROFILE = {
    "username":        "anushka_karmakar._",
    "fullName":        "Anushka Karmakar",
    "biography":       "dancer 🌸 | choreographer | spreading joy one move at a time\ncollabs → DM",
    "followersCount":  48700,
    "followingCount":  812,
    "postsCount":      234,
    "profilePicUrl":   "https://i.imgur.com/placeholder-avatar.jpg",
    "externalUrl":     "",
    "latestPosts": [
        {
            "shortCode":   "demo1",
            "displayUrl":  "https://picsum.photos/seed/dance1/600/600",
            "caption":     "Practice makes perfect ✨ new routine dropping soon",
            "likesCount":  3210,
        },
        {
            "shortCode":   "demo2",
            "displayUrl":  "https://picsum.photos/seed/dance2/600/600",
            "caption":     "Behind the scenes of our latest collab 🎬",
            "likesCount":  2870,
        },
        {
            "shortCode":   "demo3",
            "displayUrl":  "https://picsum.photos/seed/dance3/600/600",
            "caption":     "Workshop day! So grateful for everyone who showed up 💜",
            "likesCount":  4120,
        },
        {
            "shortCode":   "demo4",
            "displayUrl":  "https://picsum.photos/seed/dance4/600/600",
            "caption":     "When the music hits different 🎵",
            "likesCount":  5640,
        },
        {
            "shortCode":   "demo5",
            "displayUrl":  "https://picsum.photos/seed/dance5/600/600",
            "caption":     "Golden hour vibes 🌅",
            "likesCount":  3980,
        },
        {
            "shortCode":   "demo6",
            "displayUrl":  "https://picsum.photos/seed/dance6/600/600",
            "caption":     "Bringing the energy every single day 🔥",
            "likesCount":  4450,
        },
        {
            "shortCode":   "demo7",
            "displayUrl":  "https://picsum.photos/seed/dance7/600/600",
            "caption":     "Thank you for 40K! This community means everything 🙏",
            "likesCount":  7200,
        },
        {
            "shortCode":   "demo8",
            "displayUrl":  "https://picsum.photos/seed/dance8/600/600",
            "caption":     "New month, new moves, same passion",
            "likesCount":  2910,
        },
        {
            "shortCode":   "demo9",
            "displayUrl":  "https://picsum.photos/seed/dance9/600/600",
            "caption":     "Studio sessions ❤️‍🔥",
            "likesCount":  3340,
        },
        {
            "shortCode":   "demo10",
            "displayUrl":  "https://picsum.photos/seed/dance10/600/600",
            "caption":     "Every day is an opportunity to get better",
            "likesCount":  2780,
        },
        {
            "shortCode":   "demo11",
            "displayUrl":  "https://picsum.photos/seed/dance11/600/600",
            "caption":     "Rehearsals for the big show 🎭",
            "likesCount":  3650,
        },
        {
            "shortCode":   "demo12",
            "displayUrl":  "https://picsum.photos/seed/dance12/600/600",
            "caption":     "Dance is the hidden language of the soul 💫",
            "likesCount":  4890,
        },
    ],
}

DEMO_ABOUT = (
    "Hi, I'm Anushka — a dancer and choreographer who believes movement is the "
    "purest form of expression. I started dancing at the age of six and never "
    "looked back.\n\n"
    "Over the years I've had the privilege of performing on some incredible stages "
    "and collaborating with artists who push me to grow every single day. My style "
    "blends classical training with contemporary flair — always evolving, always "
    "authentic.\n\n"
    "When I'm not in the studio I'm teaching workshops and helping others discover "
    "the joy of movement. Follow along for behind-the-scenes content, routines, and "
    "a whole lot of good vibes."
)


# ── Main ──────────────────────────────────────────────────────────────────────

def main(demo=False):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if demo:
        print("[mode] Running in DEMO mode (no network calls)")
        profile    = DEMO_PROFILE
        about_copy = DEMO_ABOUT
        posts      = profile.get("latestPosts", [])
    else:
        # 1. Scrape Instagram profile via Apify
        profile = scrape_instagram_profile(INSTAGRAM_USER)
        posts   = profile.get("latestPosts") or profile.get("posts") or []
        print(f"[info] {len(posts)} posts fetched")

        # 2. Generate About copy (Claude or raw bio)
        print("[claude] Generating about copy …")
        about_copy = generate_about_copy(profile)

    # 3. Build HTML
    print("[build] Generating website HTML …")
    html = generate_website(profile, about_copy, posts)

    # 4. Write output files
    html_path    = os.path.join(OUTPUT_DIR, "index.html")
    profile_path = os.path.join(OUTPUT_DIR, "profile_data.json")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    print(f"\n[done] Website written to: {html_path}")
    print(f"[done] Raw profile data:    {profile_path}")
    return html_path


if __name__ == "__main__":
    import sys
    demo_mode = "--demo" in sys.argv or os.environ.get("DEMO", "").lower() in ("1", "true")
    main(demo=demo_mode)
