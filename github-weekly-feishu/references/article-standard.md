# Article Standard

Use this reference when drafting or revising the weekly GitHub article.

## Structure

1. Title: `本周 GitHub 热门内容推荐：<one natural theme sentence>`
2. Cover image
3. Metadata: data source and exact date
4. Opening: 2-3 short paragraphs explaining the week's theme
5. Summary table with columns: `项目`, `方向`, `主要价值`, `推荐理由`
6. Five project sections, each with image, repository link, and detailed explanation
7. Closing section: `本周观察`

## Tone

- Use natural, editorial Chinese.
- Avoid copying ranking language mechanically.
- Write like a knowledgeable engineer recommending projects to peers.
- Prefer concrete observations over hype.
- Explain why a project matters, not only what it does.

## Project Section Template

For each project:

```markdown
## N. owner/repo

![section image](assets/project.png)

项目地址：[owner/repo](https://github.com/owner/repo)

<What it is and why it became popular.>

<Problem, core idea, architecture/workflow, and direction.>

<Innovation, practical value, and who should read/use it.>

<Caveat if relevant: maturity, security, compliance, investment risk, or setup complexity.>

一句话推荐：**<sharp takeaway>**
```

## Output Naming

- Save the final DOCX under `F:\github每周热点\GitHub热门内容推荐`.
- The filename must be based on the previous full week before the current Monday run.
- Format: `YYYY.M.D-M.DGitHub热门内容推荐.docx`.
- Example: if the issue covers May 25-31, 2026, use `2026.5.25-5.31GitHub热门内容推荐.docx`.
- Use `scripts/build_github_weekly_docx.py article.json` without `--out` to apply this default naming rule.

## Image Standard

- Generate one cover image and one image per project.
- Use 16:9 landscape for Feishu/doc layouts.
- Make images match the article content:
  - AI rules/skills: workflow, checklists, code review, agent guardrails
  - multi-agent systems: nodes, roles, research rooms, orchestration
  - security tools: defensive dashboards, shields, logs, audit context
  - finance agents: analyst dashboards, risk indicators, market research
  - platform infrastructure: routing, task queues, memory, tools, agents
- Avoid logos, brand marks, readable UI text, fake code, malformed letters, watermarks, and real company icons.

## Feishu Delivery Standard

- If the user asks to "send the document", send a `.docx` file through the application bot, not only a long webhook message.
- If webhook text has already been sent but the user asks for a document, still upload and send the DOCX file.
- If `msg type file not support` appears, this is expected for custom webhook bots; use the application bot fallback.
- If no chat is found, ask the user to add the app bot to the group and retry.
- After sending, report success with the file name and target group. Do not repeat secrets.
