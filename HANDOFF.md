# Handoff: Spotify wishlist playlists

**Goal:** create three private Spotify playlists, **Wishlist – Tier 1 / Tier 2 / Tier 3**. Together they hold every album from the music wishlist that isn't on the Pi yet. The user wants Claude to do it, not run anything themselves.

Everything is on branch **`claude/charming-carson-2de0kg`** of `ab5trac7/help`. It isn't on `main`, so check out that branch first.

## Background (already done)

- **Source of truth:** the "Collection Shape" artifact, https://claude.ai/artifact/UvuYBeCfaw71KNLewGKJKn (16 Sep 2026). It holds a 1,541-album genre tree, matched against the music folder on the Pi (`/mnt/ssd1/data/media/music`) by folder name. Result: 177 albums owned.
- **`Music Collection Wishlist.xlsx`** (repo root) was rebuilt from that artifact's embedded data, because the original spreadsheet was never found. It has these tabs:
  - Notes
  - Albums: Family, Style, Artist, Album, Year, Origin, Tier, Owned
  - By Family / By Style: formula-driven counts
  - Want List
- **`Spotify import/Wishlist - Tier {1,2,3}.csv`** hold the missing albums (Artist, Album, Year): 311, 557 and 496 albums.
- **Why three playlists:** a Spotify playlist holds at most 10,000 tracks, and ~1,364 albums is about 15,000 tracks. The user agreed to the split.
- **Earlier blocker, now resolved:** creating a Spotify developer app needs Premium. The user has bought Premium.

## What the user still has to do

1. **Allow Spotify in the cloud environment's network settings.** The previous session was blocked from `accounts.spotify.com` and `api.spotify.com` (proxy 403). The user is in the Mac app and couldn't find the menu there, so use the browser:
   1. Go to claude.ai/code and click the cloud icon above the message box.
   2. Click **Cloud**, hover over the environment and click the gear icon.
   3. Set **Network access** to **Custom**, keeping the defaults, and add `accounts.spotify.com` and `api.spotify.com`.
   4. Save. Running sessions pick this up within about a minute.

   Check access with `curl -sS -o /dev/null -w '%{http_code}\n' https://api.spotify.com/v1/search`. A 401 means it's reachable; 000/403 means it's still blocked.
2. **Create a Spotify app:**
   1. Go to https://developer.spotify.com/dashboard and click **Create app**.
   2. Set the Redirect URI to exactly `http://127.0.0.1:8888/callback` and tick **Web API**.
   3. Send Claude the **Client ID**. No secret is needed, because the script uses PKCE.
3. **Approve the login:** open the link Claude sends, approve, then paste back the full address of the page that fails to load (`http://127.0.0.1:8888/callback?code=...`).

## Steps for Claude

Run these from `Spotify import/`:

```bash
python3 spotify_import.py auth-url  --client-id <ID>         # send the printed link to the user
python3 spotify_import.py auth-code --redirected-url '<url>'  # prints account + product (should say premium)
python3 spotify_import.py match --tier 1                      # read-only: searches Spotify, writes "Match report - Tier 1.csv"
# review the report: status ok / check / not_found; show the user the check + not_found rows
python3 spotify_import.py build --tier 1                      # creates "Wishlist – Tier 1" (private), adds tracks of 'ok' matches
python3 spotify_import.py build --tier 1 --include-check      # only after the user okays the 'check' rows
# repeat for tiers 2 and 3
```

Notes on the script (`spotify_import.py`, Python standard library only):

- **Untested against the live API.** It was written without network access. Only the syntax, the auth-URL generation and the match scoring were checked offline. Run `match` on Tier 1 first and sanity-check the results before running `build`.
- **State lives in `Spotify import/.state/`** (gitignored): the token, match results and per-playlist progress. Both `match` and `build` resume where they stopped, so re-running them is safe. Don't commit `.state/`, because it holds the user's Spotify token.
- **Matching:** it searches with `album:"…" artist:"…"` and falls back to a free-text search. It scores artist, title (ignoring remaster/deluxe suffixes), year within ±1, and album type. A score ≥17 counts as `ok`, otherwise `check`.
- **Possible 2026 API differences.** Spotify has been changing its Web API. The script tries `POST /me/playlists` and falls back to `/users/{id}/playlists`, and tries `/playlists/{id}/items` before falling back to `/tracks`. Search uses `limit=10`. If an endpoint still fails, read the error the script prints and check the current docs at developer.spotify.com.
- **Rate limits:** HTTP 429 is handled by waiting `Retry-After`. Expect `match` to take a while for 557 albums.
- **Track limit:** `build` stops before a playlist would go over 10,000 tracks.

## Caveats to tell the user

- **"Owned" was matched by folder name,** so a few albums marked missing may actually be on the Pi.
- **Some albums aren't on Spotify** or only exist in different versions; these are listed in the match reports.
- **About album types:** the rebuilt spreadsheet has no per-album type (Album/EP/Compilation), and 144 "Library" rows are owned albums that don't appear in the CSVs.

## Prompt to start the new session

> Continue the Spotify wishlist task. Check out branch `claude/charming-carson-2de0kg` and read `HANDOFF.md`. I have Spotify Premium now. Tell me what you need from me (network allowlist, Client ID, login), then build the three playlists.
