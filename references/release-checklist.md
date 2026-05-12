# Release Checklist

发布前至少检查下面这些项：

- [ ] `SKILL.md` 已存在
- [ ] `README.md` 已改成 reader-facing
- [ ] `install.sh` 可执行
- [ ] `scripts/inspect_openclaw_multi_agent.py` 可执行
- [ ] `.gitignore` 已排除敏感文件
- [ ] 没有真实 token / API key / credentials 进入仓库
- [ ] 首次成功路径写清楚
- [ ] 高优先级根因与 repair 顺序写清楚
- [ ] fresh clone 已验证
- [ ] install 已验证
- [ ] 最小调用已验证
- [ ] Root-Cause-First 巡检链已验证（至少跑一次 inspect script）
- [ ] inspect / repair 的最小证据链已定义
- [ ] 用户已明确是否要发布到 Gitee / GitHub
- [ ] 返回最终仓库 URL
