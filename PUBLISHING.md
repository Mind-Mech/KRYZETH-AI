# Publishing KRYZETH AI from Windows

The GitHub repository is `https://github.com/Mind-Mech/KRYZETH-AI`.

## 1. Rotate credentials first

The original project archive contained a local `.env` file with API credentials. Because it is unclear whether those credentials were shared elsewhere, revoke the old Groq and Fish Audio keys and create replacements before using the project publicly. Keep replacement values only in your local `.env` file. Never paste them into GitHub, chat, screenshots, or issue reports.

## 2. Extract the cleaned source snapshot

Download `KRYZETH-AI-public-review.zip` from the project owner's release-preparation conversation and extract it to a temporary folder. Keep the original project folder and original ZIP untouched.

## 3. Clone the existing repository

Open PowerShell in the folder where you keep projects:

```powershell
git clone https://github.com/Mind-Mech/KRYZETH-AI.git
```

Copy the **contents** of the extracted `KRYZETH-AI-public-review` folder into the newly cloned `KRYZETH-AI` folder. Allow the cleaned `README.md`, `.gitignore`, and other release-preparation files to replace the initial documentation where names match. Do not copy the ZIP archive itself into the repository.

For example, if both folders are in the current directory:

```powershell
Copy-Item -Path ".\KRYZETH-AI-public-review\*" -Destination ".\KRYZETH-AI\" -Recurse -Force
Set-Location .\KRYZETH-AI
```

## 4. Review and push

Inspect the changed files:

```powershell
git status --short
git diff --stat
```

Before staging, make sure the copied contents do not include `.env`, personal memory JSON, voice recordings, voice profiles, logs, downloaded model weights, or unrelated private data.

Then stage, review, commit, and push:

```powershell
git add -A
git status --short
git diff --cached --stat
git commit -m "Add cleaned KRYZETH AI source"
git push origin main
```

Use GitHub's normal browser sign-in / credential manager flow if Git requests authentication. Do not place an access token in the remote URL or commit history.

## 5. Add a license only after checking ownership

This repository intentionally has no `LICENSE` yet. Confirm that all included code and assets can legally be distributed under the chosen license before adding one. A public GitHub repository is not automatically open source.

## 6. Verify the published repository

- The README renders correctly.
- The repository contains the expected source folders.
- No secrets or personal runtime files appear.
- The repository has an appropriate license before describing it as open source.
- The project status is described as experimental, not production-ready.
