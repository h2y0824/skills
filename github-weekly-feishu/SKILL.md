---
name: github-weekly-feishu
description: Create Chinese "GitHub weekly hot projects" articles and deliver them to a Feishu/Lark group. Use when the user asks for GitHub trending/popular project recommendations, weekly GitHub content, Feishu document formatting, image-rich articles, DOCX export, recurring GitHub weekly automation, or sending the finished document to a configured Feishu group.
---

# GitHub Weekly Feishu

## Workflow

1. **Refresh current GitHub data.** Browse current GitHub Trending and project pages when the user asks for latest/weekly/current projects. Use concrete dates. Pick 5 projects per issue unless the user asks otherwise.
2. **Write the article in Feishu style.** Use natural Chinese, a short editorial intro, a summary table before project details, and one detailed section per project. Read `references/article-standard.md` when drafting or revising the article.
3. **Generate visual assets.** Use the available image generation tool for one cover image plus one project-specific image per project. If the user says "image2" but only `image_gen` is available, state that `image_gen` is being used as the available equivalent. Avoid logos, readable UI text, watermarks, and brand marks.
4. **Create a DOCX when the user wants a document/file.** Prefer a local `.docx` with embedded images. Use `scripts/build_github_weekly_docx.py` when the article can be represented as JSON. If you use the Documents skill, follow its render/QA guidance; if LibreOffice is unavailable, disclose that visual render QA was skipped.
5. **Save in the weekly output folder.** By default, save DOCX files under `F:\github每周热点\GitHub热门内容推荐`.
6. **Send to Feishu when requested.** Use `scripts/send_feishu_file.py` to upload a file and send it to the configured group. It reads credentials from environment variables; never hard-code secrets in the skill or document.

## Required Feishu Environment

Use these environment variables:

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_WEBHOOK`
- `FEISHU_CHAT_NAME`

Prefer the application bot route for files. Custom bot webhooks may reject file messages with `msg type file not support`; in that case the script uploads the file, finds the configured chat, and sends the file with the application bot.

## Article Requirements

- Include exactly 5 projects by default.
- Add a project summary table before detailed explanations.
- For every project, explain:
  - what it is
  - the problem it solves
  - core idea or architecture
  - direction/trend
  - innovation or practical value
  - caveats, compliance notes, or maturity risks when relevant
  - suitable readers/users
- End with a "本周观察" section that connects the projects into a broader trend.
- Keep the tone natural and publishable, not a stiff scraped ranking.

## Naming And Output Rules

The default DOCX filename must represent the week immediately before the current Monday run.

- If the automation runs on Monday, use the previous Monday through previous Sunday.
- Format: `YYYY.M.D-M.DGitHub热门内容推荐.docx`
- Example: a Monday run for the week after May 25-31, 2026 creates `2026.5.25-5.31GitHub热门内容推荐.docx`.
- Default folder: `F:\github每周热点\GitHub热门内容推荐`

Use the builder's default output path unless the user explicitly asks for a different path:

```powershell
python scripts/build_github_weekly_docx.py article.json
```

To preview the default output path:

```powershell
python scripts/build_github_weekly_docx.py --print-default-out
```

## File Layout For Outputs

For a normal issue in a workspace:

```text
assets/
  weekly-github-cover.png
  <project-slug>.png
article.json
GitHub热门内容推荐/
  2026.5.25-5.31GitHub热门内容推荐.docx
```

Use stable filenames so later send/retry steps can find the same artifacts.

## Useful Scripts

### Build DOCX

```powershell
python scripts/build_github_weekly_docx.py article.json
```

The JSON schema and an example can be printed with:

```powershell
python scripts/build_github_weekly_docx.py --write-sample sample-article.json
```

### Send DOCX To Feishu

```powershell
python scripts/send_feishu_file.py "F:\github每周热点\GitHub热门内容推荐\2026.5.25-5.31GitHub热门内容推荐.docx"
```

The send script:

1. obtains a tenant access token
2. uploads the file to Feishu IM
3. tries the webhook file message
4. falls back to finding `FEISHU_CHAT_NAME` and sending with the app bot

If no matching chat is found, ask the user to add the app bot to the group and retry.
