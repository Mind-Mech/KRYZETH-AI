# Publishing KRYZETH AI from Windows

The GitHub repository is `Mind-Mech/KRYZETH-AI`.

## 1. Rotate credentials first

The original project archive contained a local `.env` file with API credentials. Because it is unclear whether those credentials were shared elsewhere, revoke the old Groq and Fish Audio keys and create replacements before using the project publicly. Keep replacement values only in your local `.env` file. Never paste them into GitHub, chat, screenshots, or issue reports.

## 2. Extract the cleaned source snapshot

Download the cleaned `KRYZETH-AI-public-review.zip` supplied with this project preparation and extract it into a new folder. Keep your original project folder and original ZIP untouched.

## 3. Push the cleaned project from Windows

Open PowerShell in the extracted `KRYZETH-AI-public-review` folder.

Check Git is installed:

```powershell
git --version
```

Then verify and push:

```powershell
git init -b main
git add .
git status --short
git diff --cached --stat
```

Before committing, inspect the staged files. They must not contain `.env`, personal memory JSON, voice recordings, voice profiles, logs, downloaded model weights, or unrelated private data.

If the staged list is clean:

```powershell
git commit -m "Add cleaned KRYZETH AI source"
git remote add origin https://github.com/Mind-Mech/KRYZETH-AI.git
git push -u origin main
```

Use GitHub's normal browser sign-in / credential manager flow if Git requests authentication. Do not place an access token in the remote URL or commit history.

If the remote already contains documentation commits, first fetch and integrate them rather than force-pushing:

```powershell
git fetch origin
git pull --rebase origin main
git push -u origin main
```

## 4. Add a license only after checking ownership

This repository intentionally has no `LICENSE` yet. Confirm that all included code and assets can legally be distributed under the chosen license before adding one. A public GitHub repository is not automatically open source.

## 5. Verify the published repository

- The README renders correctly.
- The repository contains the expected source folders.
- No secrets or personal runtime files appear.
- The repository has an appropriate license before describing it as open source.
- The project status is described as experimental, not production-ready.
