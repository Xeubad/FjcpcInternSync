# .claude/hooks/stop.ps1
# 用途：会话结束前触发反思 (PowerShell 版本)
# 分层：
#   长期经验  → 写入 ~/.claude/memory/lessons.md（全局，跨项目共享）
#   任务状态  → 写入 ./tasks/*（项目本地）
# 适用：原生 Windows PowerShell（不使用 Git Bash 时）
# 部署：复制到 .claude/hooks/stop.ps1
#       settings.json 里 command 写：powershell.exe -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/stop.ps1

$ErrorActionPreference = "Continue"

@"
--- [STOP HOOK: 收尾反思清单] ---

会话即将结束 / 任务即将完成。在最终回复用户前，请检查并完成以下事项（如适用）：

## 1. 长期经验沉淀（写入全局 ~/.claude/memory/lessons.md）

本轮是否出现以下情况？任一为是 → 必须追加一条新经验到 **~/.claude/memory/lessons.md**：

- [ ] 用户明确纠正过我的方案、风格、术语或工具选择
- [ ] 出现过反复出错的问题，最终找到根因
- [ ] 学到了某个环境/依赖/接口的非显然行为
- [ ] 用户表达了"以后都这样 / 以后别这样"

**写入位置铁律**：
- 写入 **~/.claude/memory/lessons.md**（全局），不写入项目内的 lessons —— 这样所有项目都能受益
- 如果某条经验只对当前项目成立（极少数情况），在条目里明确标注 ``适用范围: 仅 <项目名>``

新经验写入格式：

``````
### [YYYY-MM-DD] 短标题
- **触发场景**：……
- **原本做法**：……
- **正确做法**：……
- **为什么**：……
- **适用范围**：全部项目 / 仅 <项目名>
``````

## 2. 项目级任务状态更新（写入 ./tasks/）

- [ ] ``tasks/in-flight.json``：当前任务是否还在进行？已完成转 done，未完成明确 progress 和 blockers
- [ ] ``tasks/feature-list.json``：本轮推进过的功能状态是否需要更新？(not_started → in_progress → passing)
- [ ] ``tasks/progress.md``：是否需要追加一条本轮里程碑？

## 3. 跨会话交接（写入 ./tasks/session-handoff.md）

如果任务未完成 / 上下文已膨胀 / 长会话即将结束，**必须**更新 handoff：

``````
### YYYY-MM-DD HH:MM — 一句话主线

已完成（已验证）：
- ……

进行中（未验证 / 部分完成）：
- ……

被阻塞：
- ……

下次会话建议第一动作：
1. ……
2. ……
``````

## 4. 验证证据收尾

- [ ] 标注的 ``passing`` 状态都有运行过的命令和结果作为证据吗？
- [ ] 没运行过验证的，是否在文档中明确说明"未验证"和"风险"？

---

[硬规则] 任一项需要更新但未做 → 必须在结束前完成，不允许只在对话里口头说"已注意"。
[硬规则] 短任务（一次性问答 / 无文件改动）可以跳过本清单，但要在最终回复里明示"本轮无需落盘"。
[硬规则] 经验写全局 lessons，任务状态写项目 tasks，不要混。

--- [STOP HOOK END] ---
"@ | Write-Output
