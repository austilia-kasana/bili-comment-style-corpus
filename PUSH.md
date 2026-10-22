# 如何把这个项目放到 GitHub（并让 GPT 读到）

本机目前**没有安装 git**。两条路，任选一条：

## 方式 A：GitHub Desktop（不需要命令行）

1. 安装 GitHub Desktop，登录你的账号。
2. `File → Add local repository`，选 `C:\Users\19536\Documents\bili-comment-style-corpus`。
3. 点 `Create repository`（如果提示 not a git repository）。
4. 右上角 `Publish repository`：
   - **只放脱敏内容 → 可以选 Public**；
   - **要放原始语料 → 必须选 Private**（见下）。
5. 发布后把仓库 URL 给 GPT（或接到 GitHub 连接器）。

## 方式 B：git 命令行

```powershell
# 1) 安装 git（任选）
winget install --id Git.Git -e
# 或：scoop install git

# 2) 初始化并提交
cd "C:\Users\19536\Documents\bili-comment-style-corpus"
git init
git add .
git commit -m "B站个人评论风格语料库：任务01-04 + 对话线"

# 3) 建远程仓库（先在 GitHub 网页建空仓库）
git branch -M main
git remote add origin https://github.com/<你的用户名>/bili-comment-style-corpus.git
git push -u origin main
```

## 要放原始语料时（仅限 Private 仓库）

默认 `.gitignore` 排除了 `raw.jsonl`、`comments.csv`、`context_review.csv`、`style_labels.csv` 等。如果你要让 GPT 读全文：

1. 确认 GitHub 仓库是 **Private**。
2. 删掉 `.gitignore` 里对应的几行（或 `git add -f data/raw.jsonl ...`）。
3. 再 commit / push。

> ⚠️ 不要把含个人日记/敏感自述的原始语料 push 到 Public 仓库。公开 = 永久公开，删了也可能有缓存。

## 让 GPT 读

- **Public 仓库**：直接把 URL 给 GPT，或接 GitHub 连接器。
- **Private 仓库**：在 GPT 的 GitHub 连接器里授权该仓库；或临时把仓库给需要的人/服务访问。
- 建议先让 GPT 读 `README.md` → `transcript/conversation.md` → `docs/`。

## 不要提交

- `~/.bili-ai/credentials.json`、任何 cookie / SESSDATA / token。
- 原始 `raw.jsonl` / `comments.csv` / `context_review.csv` / `style_labels.csv`（除非 Private 且你确认要放）。
