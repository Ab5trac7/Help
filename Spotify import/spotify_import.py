#!/usr/bin/env python3
"""Build Spotify playlists from the per-tier wishlist CSVs.

Standard library only. Uses the Authorization Code + PKCE flow, so only a
Client ID is needed (no secret).

  python3 spotify_import.py auth-url  --client-id ID
  python3 spotify_import.py auth-code --client-id ID --redirected-url 'http://127.0.0.1:8888/callback?code=...'
  python3 spotify_import.py match     --tier 1          # search Spotify, write matches, no changes to account
  python3 spotify_import.py build     --tier 1          # create/fill the playlist from the matches

State lives in .state/ next to this file (gitignored): the token, the PKCE
verifier, match results and playlist progress, so every step can be re-run
and resumes where it stopped.
"""
import argparse, base64, csv, hashlib, json, os, re, secrets, sys, time, unicodedata
import urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, ".state")
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "playlist-modify-private playlist-modify-public playlist-read-private"
API = "https://api.spotify.com/v1"
MAX_PLAYLIST_TRACKS = 10000


def spath(name):
    os.makedirs(STATE, exist_ok=True)
    return os.path.join(STATE, name)


def load(name, default=None):
    try:
        with open(spath(name), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save(name, obj):
    tmp = spath(name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, spath(name))


# ---------- auth ----------

def cmd_auth_url(a):
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    save("pkce.json", {"verifier": verifier, "client_id": a.client_id})
    q = urllib.parse.urlencode({
        "client_id": a.client_id, "response_type": "code", "redirect_uri": REDIRECT_URI,
        "code_challenge_method": "S256", "code_challenge": challenge, "scope": SCOPES,
    })
    print("https://accounts.spotify.com/authorize?" + q)


def token_request(data):
    req = urllib.request.Request("https://accounts.spotify.com/api/token",
                                 data=urllib.parse.urlencode(data).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r)
    tok["expires_at"] = time.time() + tok.get("expires_in", 3600) - 60
    return tok


def cmd_auth_code(a):
    pk = load("pkce.json")
    if not pk:
        sys.exit("Run auth-url first.")
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(a.redirected_url).query)
    if "error" in qs:
        sys.exit("Spotify returned an error: " + qs["error"][0])
    tok = token_request({"grant_type": "authorization_code", "code": qs["code"][0],
                         "redirect_uri": REDIRECT_URI, "client_id": pk["client_id"],
                         "code_verifier": pk["verifier"]})
    tok["client_id"] = pk["client_id"]
    save("token.json", tok)
    me = api("GET", "/me")
    print("Authorised as:", me.get("display_name") or me.get("id"), "| product:", me.get("product"))


def access_token():
    tok = load("token.json")
    if not tok:
        sys.exit("Not authorised. Run auth-url / auth-code first.")
    if time.time() > tok["expires_at"]:
        new = token_request({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
                             "client_id": tok["client_id"]})
        new.setdefault("refresh_token", tok["refresh_token"])
        new["client_id"] = tok["client_id"]
        save("token.json", new)
        tok = new
    return tok["access_token"]


def api(method, path, params=None, body=None, _tries=0):
    url = path if path.startswith("http") else API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + access_token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        if e.code == 429 and _tries < 8:
            time.sleep(int(e.headers.get("Retry-After", "5")) + 1)
            return api(method, path, params, body, _tries + 1)
        if e.code >= 500 and _tries < 4:
            time.sleep(2 ** _tries)
            return api(method, path, params, body, _tries + 1)
        raise RuntimeError(f"{method} {url} -> {e.code}: {e.read().decode(errors='replace')[:500]}")


# ---------- matching ----------

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\((?:[^)]*(?:remaster|deluxe|edition|expanded|anniversary|version|mono|stereo)[^)]*)\)", "", s)
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = re.sub(r"\s-\s.*(remaster|deluxe|edition|expanded|anniversary|version).*$", "", s)
    s = re.sub(r"^the\s+", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def score(row, alb):
    a_ok = any(norm(x["name"]) == norm(row["Artist"]) or norm(row["Artist"]) in norm(x["name"])
               or norm(x["name"]) in norm(row["Artist"]) for x in alb["artists"])
    t_alb, t_row = norm(alb["name"]), norm(row["Album"])
    if t_alb == t_row:
        t = 3
    elif t_row and (t_row in t_alb or t_alb in t_row):
        t = 2
    else:
        t = 0
    year = (alb.get("release_date") or "")[:4]
    y = 1 if year and row["Year"] and abs(int(year) - int(row["Year"])) <= 1 else 0
    kind = 1 if alb.get("album_type") in ("album", "compilation") else 0
    return (a_ok * 10 + t * 3 + y * 2 + kind) if a_ok and t else 0


def search(row):
    seen, cands = set(), []
    for q in (f'album:"{row["Album"]}" artist:"{row["Artist"]}"',
              f'{row["Artist"]} {row["Album"]}'):
        res = api("GET", "/search", {"q": q, "type": "album", "limit": 10})
        for alb in res.get("albums", {}).get("items", []) or []:
            if alb and alb["id"] not in seen:
                seen.add(alb["id"])
                cands.append(alb)
        if any(score(row, c) >= 19 for c in cands):  # exact artist + title + year
            break
    ranked = sorted(((score(row, c), c) for c in cands), key=lambda x: -x[0])
    return [(s, c) for s, c in ranked if s > 0]


def read_tier(tier):
    with open(os.path.join(HERE, f"Wishlist - Tier {tier}.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def cmd_match(a):
    rows = read_tier(a.tier)
    name = f"matches_tier{a.tier}.json"
    m = load(name, {})
    for i, row in enumerate(rows, 1):
        key = f'{row["Artist"]}\t{row["Album"]}'
        if key in m:
            continue
        hits = search(row)
        if not hits:
            m[key] = {"status": "not_found"}
        else:
            s, c = hits[0]
            m[key] = {"status": "ok" if s >= 17 else "check", "score": s, "id": c["id"],
                      "name": c["name"], "artist": ", ".join(x["name"] for x in c["artists"]),
                      "year": (c.get("release_date") or "")[:4], "type": c.get("album_type"),
                      "tracks": c.get("total_tracks")}
        if i % 25 == 0:
            save(name, m)
            print(f"{i}/{len(rows)}", flush=True)
    save(name, m)
    write_report(a.tier, rows, m)


def write_report(tier, rows, m):
    out = os.path.join(HERE, f"Match report - Tier {tier}.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Status", "Artist", "Album", "Year", "Spotify artist", "Spotify album",
                    "Spotify year", "Type", "Tracks", "Spotify URL"])
        for row in rows:
            r = m.get(f'{row["Artist"]}\t{row["Album"]}', {"status": "pending"})
            w.writerow([r["status"], row["Artist"], row["Album"], row["Year"], r.get("artist", ""),
                        r.get("name", ""), r.get("year", ""), r.get("type", ""), r.get("tracks", ""),
                        f'https://open.spotify.com/album/{r["id"]}' if r.get("id") else ""])
    counts = {}
    for row in rows:
        s = m.get(f'{row["Artist"]}\t{row["Album"]}', {"status": "pending"})["status"]
        counts[s] = counts.get(s, 0) + 1
    print("Tier", tier, counts, "->", out)


# ---------- playlist ----------

def album_track_uris(album_id):
    uris, url, params = [], f"/albums/{album_id}/tracks", {"limit": 50}
    while url:
        res = api("GET", url, params)
        uris += [t["uri"] for t in res.get("items", []) if t and t.get("uri")]
        url, params = res.get("next"), None
    return uris


def create_playlist(name, desc):
    body = {"name": name, "public": False, "description": desc}
    try:
        return api("POST", "/me/playlists", body=body)
    except RuntimeError:
        me = api("GET", "/me")
        return api("POST", f'/users/{me["id"]}/playlists', body=body)


def add_items(pid, uris):
    try:
        api("POST", f"/playlists/{pid}/items", body={"uris": uris})
    except RuntimeError:
        api("POST", f"/playlists/{pid}/tracks", body={"uris": uris})


def cmd_build(a):
    rows = read_tier(a.tier)
    m = load(f"matches_tier{a.tier}.json")
    if not m:
        sys.exit("Run match first.")
    statuses = {"ok", "check"} if a.include_check else {"ok"}
    prog_name = f"playlist_tier{a.tier}.json"
    prog = load(prog_name, {"id": None, "done": [], "count": 0})
    if not prog["id"]:
        pl = create_playlist(f"Wishlist – Tier {a.tier}",
                             f"Tier {a.tier} albums from the music wishlist that aren't on the Pi yet.")
        prog["id"] = pl["id"]
        save(prog_name, prog)
        print("Created playlist", pl.get("external_urls", {}).get("spotify", pl["id"]))
    done = set(prog["done"])
    for row in rows:
        key = f'{row["Artist"]}\t{row["Album"]}'
        r = m.get(key)
        if key in done or not r or r["status"] not in statuses:
            continue
        uris = album_track_uris(r["id"])
        if prog["count"] + len(uris) > MAX_PLAYLIST_TRACKS:
            sys.exit(f"Stopping: playlist would exceed {MAX_PLAYLIST_TRACKS} tracks at {key!r}.")
        for i in range(0, len(uris), 100):
            add_items(prog["id"], uris[i:i + 100])
        prog["done"].append(key)
        prog["count"] += len(uris)
        save(prog_name, prog)
    print(f'Tier {a.tier}: {len(prog["done"])} albums, {prog["count"]} tracks -> '
          f'https://open.spotify.com/playlist/{prog["id"]}')


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("auth-url"); s.add_argument("--client-id", required=True)
    s = sub.add_parser("auth-code"); s.add_argument("--client-id"); s.add_argument("--redirected-url", required=True)
    s = sub.add_parser("match"); s.add_argument("--tier", type=int, choices=[1, 2, 3], required=True)
    s = sub.add_parser("build"); s.add_argument("--tier", type=int, choices=[1, 2, 3], required=True)
    s.add_argument("--include-check", action="store_true", help="also add albums whose match status is 'check'")
    a = p.parse_args()
    {"auth-url": cmd_auth_url, "auth-code": cmd_auth_code, "match": cmd_match, "build": cmd_build}[a.cmd](a)


if __name__ == "__main__":
    main()
