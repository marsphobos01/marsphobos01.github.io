#!/usr/bin/env python3
"""
blog_tool.py — a tiny local publishing UI for marsphobos.com

Run:
    pip install flask markdown
    python3 blog_tool.py
Then open http://localhost:5000 in your browser.

What it does on "Save post":
  1. Creates  posts/<slug>.html   (full article page, matching the site template)
  2. Adds a row to the top of the list in  blog.html
  3. Adds a matching entry to blog.html's JSON-LD  blogPost  array
  4. Adds a <url> entry to  sitemap.xml

"Publish" then runs: git add -A && git commit && git push  (current branch).
Live preview is rendered with marked.js; the saved file is rendered with Python-Markdown.
"""

import re
import json
import html
import subprocess
import datetime
from pathlib import Path

try:
    import markdown as md_lib
except ImportError:
    md_lib = None

try:
    from flask import Flask, request, jsonify
except ImportError:
    raise SystemExit("Flask is not installed. Run:  pip install flask markdown")

# ---------------------------------------------------------------- config
def _find_site_root(start):
    """Walk up from the script until we find the repo root (where blog.html lives)."""
    p = start
    for _ in range(6):
        if (p / "blog.html").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return start

SITE_ROOT = _find_site_root(Path(__file__).resolve().parent)
POSTS_DIR = SITE_ROOT / "posts"
BLOG_FILE = SITE_ROOT / "blog.html"
SITEMAP   = SITE_ROOT / "sitemap.xml"
SITE_URL  = "https://marsphobos.com"
AUTHOR    = "Morgan Bennett"

esc = lambda s: html.escape(s or "", quote=True)

app = Flask(__name__)

# ---------------------------------------------------------------- helpers
def slugify(title):
    s = (title or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "untitled"

def display_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b %Y')}"

def read_time(body_md):
    words = len(re.findall(r"\w+", body_md or ""))
    return f"{max(1, round(words / 200))} min read"

def md_to_html(text):
    if md_lib is None:
        # minimal fallback: blank-line paragraphs only
        paras = [p.strip() for p in (text or "").split("\n\n") if p.strip()]
        return "\n".join(f"<p>{esc(p)}</p>" for p in paras)
    out = md_lib.markdown(text or "", extensions=["extra", "sane_lists"])
    # the page <h1> is the post title, so demote any body h1 to h2
    out = re.sub(r"<(/?)h1>", r"<\1h2>", out)
    return out

def get_branch():
    try:
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                           cwd=SITE_ROOT, capture_output=True, text=True)
        return r.stdout.strip() or "?"
    except Exception:
        return "?"

# ---------------------------------------------------------------- post page
POST_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@@TITLE@@ — Morgan Bennett</title>
    <meta name="description" content="@@DESC@@">
    <meta name="theme-color" content="#f0ebe8">
    <link rel="canonical" href="@@URL@@">
    <link rel="icon" href="../favicon.svg" type="image/svg+xml">

    <meta property="og:type" content="article">
    <meta property="og:title" content="@@TITLE@@">
    <meta property="og:description" content="@@DESC@@">
    <meta property="og:url" content="@@URL@@">
    <meta property="og:image" content="@@SITE@@/banner.jpg">
    <meta property="og:image:alt" content="Morgan Bennett — developer blog">
    <meta property="article:published_time" content="@@DATE_ISO@@">
    <meta property="article:author" content="Morgan Bennett">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="@@TITLE@@">
    <meta name="twitter:description" content="@@DESC@@">
    <meta name="twitter:image" content="@@SITE@@/banner.jpg">
    <meta name="twitter:site" content="@mars_ph0b05">

    <script type="application/ld+json">
@@JSONLD@@
    </script>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Syne:wght@500;600;700;800&family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../styles.css">
</head>
<body id="top">

<header class="site-header" id="header">
    <div class="container nav">
        <a href="/" class="brand">Morgan Bennett</a>
        <nav class="nav-links" id="navLinks" aria-label="Primary">
            <a href="/">Home</a>
            <a href="/projects">Projects</a>
            <a href="/blog" aria-current="page">Blog</a>
            <a href="/#about">About</a>
            <a href="/#contact">Contact</a>
        </nav>
        <button class="menu-toggle" id="menuToggle" type="button" aria-label="Toggle menu" aria-expanded="false"><span></span><span></span><span></span></button>
    </div>
</header>

<main>
    <article class="article">
        <div class="container">
            <div class="article-inner">
                <a class="back-link" href="/blog">← Back to blog</a>
                <div class="meta"><span>@@DATE_DISP@@</span><span class="tag">@@TAG@@</span><span>@@READ@@</span></div>
                <h1>@@TITLE@@</h1>
                <div class="article-body">
@@BODY@@
                </div>
            </div>
        </div>
    </article>
</main>

<footer>
    <div class="container footer-grid">
        <span>© <span id="year">2026</span> Morgan Bennett — mars_phobos</span>
        <a href="#top">Back to top ↑</a>
    </div>
</footer>

<script src="../main.js"></script>
</body>
</html>
"""

def build_post_html(title, desc, slug, date_iso, tag, read, body_html):
    url = f"{SITE_URL}/posts/{slug}"
    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "description": desc,
        "image": f"{SITE_URL}/banner.jpg",
        "datePublished": date_iso,
        "dateModified": date_iso,
        "url": url,
        "mainEntityOfPage": url,
        "author": {"@type": "Person", "name": AUTHOR, "url": f"{SITE_URL}/"},
        "publisher": {"@type": "Person", "name": AUTHOR},
    }, indent=2)
    repl = {
        "@@TITLE@@": esc(title), "@@DESC@@": esc(desc), "@@URL@@": url,
        "@@SITE@@": SITE_URL, "@@DATE_ISO@@": date_iso,
        "@@DATE_DISP@@": esc(display_date(date_iso)), "@@TAG@@": esc(tag),
        "@@READ@@": esc(read), "@@JSONLD@@": jsonld, "@@BODY@@": body_html,
    }
    out = POST_TEMPLATE
    for k, v in repl.items():
        out = out.replace(k, v)
    return out

# ---------------------------------------------------------------- file edits
def insert_blog_row(title, desc, slug, date_disp, tag):
    row = (
        '\n                <a class="post-row reveal" href="/posts/' + slug + '">\n'
        '                    <span class="post-date">' + esc(date_disp) + '</span>\n'
        '                    <div class="post-main">\n'
        '                        <span class="post-tag">' + esc(tag) + '</span>\n'
        '                        <h3>' + esc(title) + '</h3>\n'
        '                        <p>' + esc(desc) + '</p>\n'
        '                    </div>\n'
        '                    <span class="post-arrow">↗</span>\n'
        '                </a>\n'
    )
    anchor = "<!-- POST: duplicate this block + the matching post page for each new entry -->"
    content = BLOG_FILE.read_text(encoding="utf-8")
    if anchor not in content:
        raise RuntimeError("Could not find the post-list anchor comment in blog.html")
    BLOG_FILE.write_text(content.replace(anchor, anchor + row, 1), encoding="utf-8")

def insert_jsonld(title, slug, date_iso):
    entry = (
        '        {\n'
        '          "@type": "BlogPosting",\n'
        '          "headline": ' + json.dumps(title) + ',\n'
        '          "url": "' + SITE_URL + '/posts/' + slug + '",\n'
        '          "datePublished": "' + date_iso + '",\n'
        '          "author": { "@type": "Person", "name": "' + AUTHOR + '" }\n'
        '        },\n'
    )
    needle = '"blogPost": [\n'
    content = BLOG_FILE.read_text(encoding="utf-8")
    if needle not in content:
        return  # JSON-LD is optional; skip quietly if structure differs
    BLOG_FILE.write_text(content.replace(needle, needle + entry, 1), encoding="utf-8")

def insert_sitemap(slug, date_iso):
    entry = ('  <url><loc>' + SITE_URL + '/posts/' + slug + '</loc>'
             '<lastmod>' + date_iso + '</lastmod>'
             '<changefreq>monthly</changefreq><priority>0.6</priority></url>\n')
    content = SITEMAP.read_text(encoding="utf-8")
    if "</urlset>" in content:
        SITEMAP.write_text(content.replace("</urlset>", entry + "</urlset>", 1), encoding="utf-8")

# ---------------------------------------------------------------- routes
@app.route("/save", methods=["POST"])
def save():
    d = request.get_json(force=True)
    title = (d.get("title") or "").strip()
    body  = d.get("body") or ""
    if not title:
        return jsonify(ok=False, error="A title is required.")
    if not body.strip():
        return jsonify(ok=False, error="The post body is empty.")
    slug = slugify(d.get("slug") or title)
    desc = (d.get("summary") or "").strip() or title
    tag  = (d.get("tag") or "Note").strip()
    date_iso = (d.get("date") or datetime.date.today().isoformat()).strip()
    read = (d.get("readtime") or "").strip() or read_time(body)

    try:
        datetime.date.fromisoformat(date_iso)
    except ValueError:
        return jsonify(ok=False, error="Date must be YYYY-MM-DD.")

    post_path = POSTS_DIR / f"{slug}.html"
    if post_path.exists() or f'/posts/{slug}"' in BLOG_FILE.read_text(encoding="utf-8"):
        return jsonify(ok=False, error=f"A post with slug '{slug}' already exists. Pick a different title/slug.")

    try:
        POSTS_DIR.mkdir(exist_ok=True)
        body_html = md_to_html(body)
        post_path.write_text(build_post_html(title, desc, slug, date_iso, tag, read, body_html), encoding="utf-8")
        insert_blog_row(title, desc, slug, display_date(date_iso), tag)
        insert_jsonld(title, slug, date_iso)
        insert_sitemap(slug, date_iso)
    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}")

    return jsonify(ok=True, slug=slug,
                   message=f"Saved posts/{slug}.html and updated blog.html + sitemap.xml.")

@app.route("/publish", methods=["POST"])
def publish():
    d = request.get_json(force=True) or {}
    msg = (d.get("message") or "Add blog post").strip()
    steps = [["git", "add", "-A"],
             ["git", "commit", "-m", msg],
             ["git", "push", "origin", "HEAD"]]
    log = []
    for cmd in steps:
        r = subprocess.run(cmd, cwd=SITE_ROOT, capture_output=True, text=True)
        log.append("$ " + " ".join(cmd) + "\n" + (r.stdout + r.stderr).strip())
        if r.returncode != 0 and cmd[1] != "commit":  # 'nothing to commit' is non-fatal
            return jsonify(ok=False, log="\n\n".join(log))
    return jsonify(ok=True, log="\n\n".join(log), branch=get_branch())

@app.route("/")
def index():
    return PAGE.replace("@@BRANCH@@", esc(get_branch())) \
               .replace("@@TODAY@@", datetime.date.today().isoformat()) \
               .replace("@@MDWARN@@", "" if md_lib else
                        "Markdown library not found — run  pip install markdown  for proper formatting.")

# ---------------------------------------------------------------- UI page
PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>New post · marsphobos</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/4.3.0/marked.min.js"></script>
<style>
  :root{--paper:#f0ebe8;--ink:#141820;--accent:#c0603a;--line:rgba(20,24,32,0.14);}
  *{box-sizing:border-box;}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--paper);color:var(--ink);}
  header{padding:18px 28px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;}
  header b{font-size:15px;} header .b{font-size:12px;color:#6b6b6b;}
  .wrap{display:flex;gap:0;height:calc(100vh - 59px);}
  .col{flex:1;min-width:0;overflow:auto;padding:24px 28px;}
  .col.preview{border-left:1px solid var(--line);background:#fff;}
  label{display:block;font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:#6b6b6b;margin:14px 0 5px;}
  input,textarea,select{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:8px;font-size:14px;font-family:inherit;background:#fff;color:var(--ink);}
  textarea{resize:vertical;} #body{min-height:340px;font-family:ui-monospace,Menlo,monospace;font-size:13px;line-height:1.55;}
  .row{display:flex;gap:12px;} .row>div{flex:1;}
  .bar{display:flex;gap:10px;align-items:center;margin-top:18px;flex-wrap:wrap;}
  button{padding:11px 20px;border-radius:100px;border:1px solid var(--ink);background:none;color:var(--ink);font-size:14px;font-weight:600;cursor:pointer;}
  button.primary{background:var(--accent);border-color:var(--accent);color:#fff;}
  button:disabled{opacity:.5;cursor:default;}
  #status{margin-top:14px;font-size:13px;white-space:pre-wrap;padding:12px;border-radius:8px;display:none;}
  #status.ok{display:block;background:#e6f3ea;color:#1f5135;}
  #status.err{display:block;background:#f6e4e1;color:#7a2c1a;}
  #status.log{display:block;background:#1c2027;color:#d6d2c8;font-family:ui-monospace,Menlo,monospace;font-size:12px;}
  .warn{font-size:12px;color:#7a2c1a;margin-top:8px;}
  .preview h1{font-size:30px;margin:.2em 0;} .preview h2{font-size:20px;margin:1.4em 0 .4em;}
  .preview p,.preview li{font-size:15px;line-height:1.7;color:#33363d;}
  .preview blockquote{border-left:3px solid var(--accent);margin:0;padding-left:14px;color:#444;font-style:italic;}
  .preview code{background:#efe9e4;padding:2px 5px;border-radius:4px;font-size:.9em;}
  .meta-pre{font-size:12px;color:#6b6b6b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px;}
</style></head>
<body>
<header><b>New blog post</b><span class="b">repo branch: <code>@@BRANCH@@</code></span></header>
<div class="wrap">
  <div class="col">
    <label>Title</label>
    <input id="title" placeholder="Remastering Resleeve: rebuilding it properly">
    <div class="row">
      <div><label>Slug (URL)</label><input id="slug" placeholder="auto from title"></div>
      <div><label>Tag</label><input id="tag" list="tags" value="Note"><datalist id="tags"><option>Project<option>Note<option>Guide<option>Build log<option>Update</datalist></div>
    </div>
    <div class="row">
      <div><label>Date</label><input id="date" type="date" value="@@TODAY@@"></div>
      <div><label>Read time</label><input id="readtime" placeholder="auto"></div>
    </div>
    <label>Summary (one line, shown on the blog list)</label>
    <textarea id="summary" rows="2" placeholder="A short hook describing the post."></textarea>
    <label>Body — Markdown ( ## heading · - list · &gt; quote · `code` · [text](url) )</label>
    <textarea id="body" placeholder="Write your post here in Markdown..."></textarea>
    <div class="warn">@@MDWARN@@</div>
    <div class="bar">
      <button class="primary" id="saveBtn">Save post</button>
      <button id="pubBtn">Publish to GitHub</button>
    </div>
    <div id="status"></div>
  </div>
  <div class="col preview">
    <div class="meta-pre" id="pvMeta"></div>
    <h1 id="pvTitle"></h1>
    <div id="pvBody" class="preview"></div>
  </div>
</div>
<script>
const $ = id => document.getElementById(id);
let slugEdited = false;
$("slug").addEventListener("input", () => slugEdited = true);
function slugify(t){return t.toLowerCase().replace(/[^a-z0-9\\s-]/g,"").replace(/[\\s_-]+/g,"-").replace(/^-+|-+$/g,"");}
function render(){
  if(!slugEdited) $("slug").value = slugify($("title").value);
  const words = ($("body").value.match(/\\w+/g)||[]).length;
  $("readtime").placeholder = Math.max(1, Math.round(words/200)) + " min read";
  $("pvTitle").textContent = $("title").value || "Untitled";
  const d = $("date").value, tag = $("tag").value, rt = $("readtime").value || $("readtime").placeholder;
  $("pvMeta").textContent = [d, tag, rt].filter(Boolean).join("  ·  ");
  $("pvBody").innerHTML = marked.parse($("body").value || "");
}
["title","slug","tag","date","readtime","body"].forEach(id => $(id).addEventListener("input", render));
render();

function show(cls, text){const s=$("status"); s.className=cls; s.textContent=text;}
$("saveBtn").onclick = async () => {
  show("", ""); $("saveBtn").disabled = true;
  try{
    const payload = {title:$("title").value, slug:$("slug").value, tag:$("tag").value,
      date:$("date").value, readtime:$("readtime").value, summary:$("summary").value, body:$("body").value};
    const r = await fetch("/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    const j = await r.json();
    if(j.ok) show("ok", "✓ " + j.message + "\\n\\nPreview locally with a server, then click Publish when ready.");
    else show("err", "✗ " + j.error);
  }catch(e){ show("err", "✗ " + e); }
  $("saveBtn").disabled = false;
};
$("pubBtn").onclick = async () => {
  if(!confirm("Commit all changes and push to GitHub (branch: @@BRANCH@@)?")) return;
  show("", ""); $("pubBtn").disabled = true;
  try{
    const msg = "Add blog post: " + ($("title").value || "untitled");
    const r = await fetch("/publish",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:msg})});
    const j = await r.json();
    show("log", (j.ok ? "✓ Pushed.\\n\\n" : "✗ Git error.\\n\\n") + j.log);
  }catch(e){ show("err", "✗ " + e); }
  $("pubBtn").disabled = false;
};
</script>
</body></html>
"""

if __name__ == "__main__":
    print("\n  Blog tool running →  http://localhost:5000")
    print(f"  Editing site at:    {SITE_ROOT}\n")
    app.run(port=5000, debug=False)
