# Build Your AI Brain
## How to Export, Visualize & Search Your Entire ChatGPT and Claude History

*Alex Freedman ([@alex2learn](https://alex2learn.com)) — March 2026*

---

## Table of Contents

1. Prerequisites
2. Export Your Data
3. Set Up Your Vault
4. Let Claude Code Do the Work
5. What You'll Get
6. Next Steps

---

## Section 01 — Prerequisites

> ⚠️ **IMPORTANT:** If you don't have Claude Code, do not continue. You're going to need Claude Code to tag and link your chats — they won't automatically connect without it. I'll be posting Claude Code tutorials on my profile, so follow for that.

### What You Need

- **Claude Code (CLI)** — the engine that organizes everything
- **Obsidian (free)** — the app that visualizes your vault
- **Your chat exports** from ChatGPT and/or Claude

> This tutorial covers ChatGPT and Claude exports only. iMessages and Apple Notes will be covered in a following tutorial.

---

## Section 02 — Export Your Data

### Claude (Fastest — ~5 minutes)

1. Go to [claude.ai](https://claude.ai)
2. Click your profile icon (bottom-left)
3. Go to **Settings**
4. Click **"Export Data"** under Privacy
5. You'll get an email within 5 minutes with a download link
6. Download and unzip — you'll get a `conversations.json` file

### ChatGPT (Takes 1–3 days)

1. Go to [chatgpt.com](https://chatgpt.com)
2. Click your profile icon → **Settings**
3. Go to **Data Controls**
4. Click **"Export data"**
5. You'll get an email (can take up to a few days — be patient)
6. Download the ZIP from the email link and unzip it
7. You'll find multiple `conversations-XXX.json` files

> 💡 **PRO TIP:** Claude sends your export in under 5 minutes. OpenAI can take days. Start your ChatGPT export first, then do Claude while you wait.

---

## Section 03 — Set Up Your Vault

1. Download Obsidian from [obsidian.md](https://obsidian.md) (free)
2. Create a folder on your desktop called `Brain`
3. Put your Claude and ChatGPT export folders inside it
4. Open Obsidian → **"Open folder as vault"** → select `Brain`

---

## Section 04 — Let Claude Code Do the Work

1. Open your terminal
2. Navigate to your Brain folder:
   ```bash
   cd ~/Desktop/Brain
   ```
3. Run `claude` to start Claude Code
4. Tell it:
   ```
   Organize this folder into an Obsidian vault. Convert all my
   ChatGPT and Claude conversations into individual markdown files
   with proper frontmatter (title, date, tags, category). Then
   launch 10 sub-agents to go through every conversation and
   smartly tag things — names, people, places, recurring themes,
   projects, and topics. Link everything together with wikilinks
   so the Obsidian graph connects related conversations.
   ```
5. Let it run — Claude Code will create subagents that process everything in parallel
6. When it's done, go back to Obsidian and hit `Cmd+G` (Mac) or `Ctrl+G` (Windows) to see your graph

---

## Section 05 — What You'll Get

- Every conversation as a searchable markdown file
- Tags and categories on everything
- A visual graph showing how your ideas, projects, and conversations connect
- Full-text search across your entire AI history
- Entity pages for people, projects, and topics that link all related conversations

### Real-World Results

> I ran this on 2,021 ChatGPT conversations and 363 Claude conversations spanning 3+ years. The result is a 5,000+ file vault with 14 AI-generated insight reports, entity pages for 80+ people and projects, and a graph that connects everything from my first GPT prompt ("How did Andrew Tate get rich?") to my latest Claude Code session.

---

## Section 06 — Next Steps

- Follow [@alex2learn](https://alex2learn.com) for the Claude Code setup tutorial
- Coming soon: Adding iMessages, Apple Notes, and voice memos to your vault
- Pro tip: Run a sync script periodically to keep your vault updated with new Claude Code sessions

### Platform Export Reference

| Platform     | Export Time  | File Format              | Where to Find It                          |
|--------------|--------------|--------------------------|-------------------------------------------|
| Claude       | ~5 minutes   | `conversations.json`     | Settings → Privacy → Export Data          |
| ChatGPT      | 1–3 days     | `conversations-XXX.json` | Settings → Data Controls → Export         |
| iMessages    | Coming soon  | TBD                      | Follow @alex2learn for updates            |
| Apple Notes  | Coming soon  | TBD                      | Follow @alex2learn for updates            |

---

## Your Brain Vault Checklist

- [ ] Export Claude data (Settings → Privacy → Export Data)
- [ ] Export ChatGPT data (Settings → Data Controls → Export)
- [ ] Download and install Obsidian from [obsidian.md](https://obsidian.md)
- [ ] Create `Brain` folder and add exports
- [ ] Open folder as Obsidian vault
- [ ] Run Claude Code to organize, tag, and link everything
- [ ] Explore your graph view (`Cmd+G` / `Ctrl+G`)
- [ ] Follow [@alex2learn](https://alex2learn.com) for the Claude Code tutorial and future updates

> 💡 **PRO TIP:** Bookmark [alex2learn.com](https://alex2learn.com) and follow @alex2learn on social media. The Claude Code setup tutorial, iMessage import guide, and Apple Notes integration are all coming soon.
