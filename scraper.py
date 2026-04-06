import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import re
import socket
import threading
from utils import save_text, save_json, save_image

TOR_PROXY = {
    "http":  "socks5h://127.0.0.1:9050",
    "https": "socks5h://127.0.0.1:9050"
}

_stop_flag = threading.Event()


def set_stop():
    _stop_flag.set()


def clear_stop():
    _stop_flag.clear()


def is_stopped():
    return _stop_flag.is_set()


def check_tor_running():
    try:
        s = socket.create_connection(("127.0.0.1", 9050), timeout=3)
        s.close()
        return True
    except (socket.error, ConnectionRefusedError):
        return False


def get_session():
    session = requests.Session()
    session.proxies = TOR_PROXY
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"
    })
    return session


def make_site_folder(base_folder, url):
    """
    Creates a named subfolder based on the site hostname.
    e.g. base/facebookcorewwwi.onion/2024-01-01_12-00-00/
    """
    import time
    parsed   = urlparse(url)
    hostname = parsed.netloc or parsed.path.split("/")[0]
    hostname = re.sub(r"[^\w.-]", "_", hostname)
    ts       = time.strftime("%Y-%m-%d_%H-%M-%S")
    folder   = os.path.join(base_folder, hostname, ts)
    os.makedirs(folder, exist_ok=True)
    return folder, hostname


def scrape(url, output_folder, options=None, log_callback=None):
    def log(msg):
        if log_callback:
            log_callback(msg)

    def stopped():
        if is_stopped():
            log("[STOPPED] Scrape cancelled by user.")
            return True
        return False

    clear_stop()

    if options is None:
        options = {k: True for k in
                   ["text", "links", "images", "videos", "audio", "files", "emails"]}

    log("[CHECK]  Verifying Tor on 127.0.0.1:9050...")
    if not check_tor_running():
        log("[ERROR]  Tor is NOT running.")
        log("[FIX]    Run: sudo service tor start")
        return

    log("[OK]     Tor is active.")
    session = get_session()

    log(f"[FETCH]  {url}")
    try:
        response = session.get(url, timeout=90)
        response.raise_for_status()
    except requests.exceptions.ConnectTimeout:
        log("[ERROR]  Timed out. Site may be offline or slow.")
        log("[TIP]    Wait a few seconds and retry.")
        return
    except requests.exceptions.ConnectionError as e:
        log(f"[ERROR]  {e}")
        log("[TIP]    Confirm Tor is running: sudo service tor start")
        return
    except Exception as e:
        log(f"[ERROR]  {e}")
        return

    if stopped():
        return

    log(f"[OK]     HTTP {response.status_code}")

    # Create named folder: base/hostname/timestamp/
    site_folder, hostname = make_site_folder(output_folder, url)
    log(f"[FOLDER] {site_folder}")

    soup = BeautifulSoup(response.text, "html.parser")

    # Page title
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else hostname
    log(f"[INFO]   Page title: {page_title}")

    # Save metadata
    import time as _time
    meta = {
        "url":       url,
        "hostname":  hostname,
        "title":     page_title,
        "status":    response.status_code,
        "scraped_at": _time.strftime("%Y-%m-%d %H:%M:%S"),
        "options":   options
    }
    save_json(site_folder, "meta.json", meta)
    log("[SAVED]  meta.json")

    # Save raw HTML
    save_text(site_folder, "page_source.html", response.text)
    log("[SAVED]  page_source.html")

    # ── Text ──────────────────────────────────────────────────────
    if options.get("text") and not stopped():
        text = soup.get_text(separator="\n", strip=True)
        save_text(site_folder, "text.txt", text)
        log(f"[SAVED]  text.txt  ({len(text):,} chars)")

    # ── Emails ────────────────────────────────────────────────────
    if options.get("emails") and not stopped():
        raw = soup.get_text()
        emails = list(set(re.findall(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", raw
        )))
        if emails:
            save_json(site_folder, "emails.json", emails)
            log(f"[SAVED]  emails.json  ({len(emails)} found)")
        else:
            log("[INFO]   No emails found.")

    # ── Links ─────────────────────────────────────────────────────
    if options.get("links") and not stopped():
        links = []
        for tag in soup.find_all("a", href=True):
            full = urljoin(url, tag["href"])
            links.append({
                "text":  tag.get_text(strip=True),
                "url":   full,
                "onion": ".onion" in full
            })
        save_json(site_folder, "links.json", links)
        onion = sum(1 for l in links if l["onion"])
        log(f"[SAVED]  links.json  ({len(links)} total, {onion} .onion)")

    # ── Images ────────────────────────────────────────────────────
    if options.get("images") and not stopped():
        IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico"}
        img_folder = os.path.join(site_folder, "images")
        os.makedirs(img_folder, exist_ok=True)
        srcs = []
        for tag in soup.find_all("img"):
            s = tag.get("src") or tag.get("data-src")
            if s:
                srcs.append(urljoin(url, s))
        for a in soup.find_all("a", href=True):
            ext = os.path.splitext(urlparse(a["href"]).path)[-1].lower()
            if ext in IMAGE_EXTS:
                srcs.append(urljoin(url, a["href"]))
        srcs = list(dict.fromkeys(srcs))
        count = 0
        for i, src in enumerate(srcs):
            if stopped():
                break
            try:
                data = session.get(src, timeout=20).content
                ext  = os.path.splitext(urlparse(src).path)[-1] or ".jpg"
                save_image(img_folder, f"img_{i+1}{ext}", data)
                count += 1
                log(f"[IMG]    {i+1}/{len(srcs)}  {src[:70]}")
            except Exception as e:
                log(f"[WARN]   Image {i+1} failed: {e}")
        log(f"[SAVED]  images/  ({count} downloaded)")

    # ── Videos ───────────────────────────────────────────────────
    if options.get("videos") and not stopped():
        VIDEO_EXTS = {".mp4", ".webm", ".mkv", ".avi", ".mov", ".ogv"}
        vids = []
        for tag in soup.find_all(["video", "source"]):
            s = tag.get("src")
            if s:
                vids.append(urljoin(url, s))
        for a in soup.find_all("a", href=True):
            ext = os.path.splitext(urlparse(a["href"]).path)[-1].lower()
            if ext in VIDEO_EXTS:
                vids.append(urljoin(url, a["href"]))
        vids = list(set(vids))
        if vids:
            save_json(site_folder, "videos.json", vids)
            log(f"[SAVED]  videos.json  ({len(vids)} found)")
        else:
            log("[INFO]   No videos found.")

    # ── Audio ─────────────────────────────────────────────────────
    if options.get("audio") and not stopped():
        AUDIO_EXTS = {".mp3", ".ogg", ".wav", ".flac", ".aac", ".m4a"}
        audio = []
        for tag in soup.find_all(["audio", "source"]):
            s = tag.get("src")
            if s:
                audio.append(urljoin(url, s))
        for a in soup.find_all("a", href=True):
            ext = os.path.splitext(urlparse(a["href"]).path)[-1].lower()
            if ext in AUDIO_EXTS:
                audio.append(urljoin(url, a["href"]))
        audio = list(set(audio))
        if audio:
            save_json(site_folder, "audio.json", audio)
            log(f"[SAVED]  audio.json  ({len(audio)} found)")
        else:
            log("[INFO]   No audio found.")

    # ── Files ─────────────────────────────────────────────────────
    if options.get("files") and not stopped():
        FILE_EXTS = {".pdf", ".doc", ".docx", ".zip", ".tar", ".gz",
                     ".7z", ".rar", ".exe", ".apk", ".iso", ".csv"}
        files = []
        for a in soup.find_all("a", href=True):
            ext = os.path.splitext(urlparse(a["href"]).path)[-1].lower()
            if ext in FILE_EXTS:
                files.append({
                    "text": a.get_text(strip=True),
                    "url":  urljoin(url, a["href"]),
                    "ext":  ext
                })
        if files:
            save_json(site_folder, "files.json", files)
            log(f"[SAVED]  files.json  ({len(files)} found)")
        else:
            log("[INFO]   No downloadable files found.")

    if not is_stopped():
        log(f"\n[DONE]   Saved to: {site_folder}")