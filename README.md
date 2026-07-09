# client-brief-public-form

客户公网需求表单 v1。这个小仓库只负责客户填写页，不包含“小快乐工作室”的内部工作台、API 设置、项目数据和图生视频功能。

## 部署组件

- Streamlit Community Cloud：托管 `public_brief_app.py`
- Supabase Free：保存表单记录
- SMTP：客户提交后发送提醒邮件

## Supabase 初始化

1. 在 Supabase SQL Editor 执行 `supabase_setup.sql`。
2. 本地“小快乐工作室”里填写 Supabase URL、service key、公网表单地址。
3. Streamlit Secrets 只填写 `SUPABASE_URL` 和 `SUPABASE_ANON_KEY`，不要把 service key 放进公网仓库。

## Streamlit Secrets

复制 `.streamlit/secrets.example.toml` 到 Streamlit Community Cloud 的 Secrets 页面，并填写：

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_ANON_KEY = "..."

SMTP_HOST = "smtp.example.com"
SMTP_PORT = 587
SMTP_USERNAME = "..."
SMTP_PASSWORD = "..."
SMTP_FROM = "brief@example.com"
NOTIFY_TO = "you@example.com"
```

SMTP 为空时，客户仍可提交，只是不发送邮件提醒。

## 本地同步模板

在“小快乐工作室 > 需求表单 > 客户公网表单设置”点击 `同步公网表单模板`，会覆盖本仓库的 `public_form_schema.json`。v1 不自动 commit/push；发布到 Streamlit Cloud 后，回到本地点击 `我已发布，关闭提醒`。
