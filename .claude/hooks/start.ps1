# .claude/hooks/start.ps1
# 用途：会话开始时自动注入 tasks/（项目级） + memory/（全局）上下文（PowerShell 版本）
# 分层：
#   tasks/      → 项目本地，每个项目独立（功能进度、handoff、in-flight）
#   memory/     → 全局 ~/.claude/memory/，跨项目共享（lessons、长期偏好）
# 适用：原生 Windows PowerShell（不使用 Git Bash 时）
# 部署：复制到 .claude/hooks/start.ps1
#       settings.json 里 command 写：powershell.exe -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/start.ps1

$ErrorActionPreference = "Continue"

Write-Output "--- [SESSION START CONTEXT INJECTION] ---"
Write-Output ""

# ============================================================
# 项目级任务运行态（tasks/ 在项目根）
# ============================================================
if (Test-Path "tasks") {
    Write-Output "## [项目级] 当前项目运行态 (./tasks/)"
    Write-Output ""

    # 1. handoff
    if (Test-Path "tasks/session-handoff.md") {
        Write-Output "### 1. 上次任务交接 (tasks/session-handoff.md)"
        Get-Content -Path "tasks/session-handoff.md" -TotalCount 30
        Write-Output ""
        Write-Output "..."
        Write-Output ""
    }

    # 2. in-flight
    if (Test-Path "tasks/in-flight.json") {
        Write-Output "### 2. 当前进行中的任务 (tasks/in-flight.json)"
        Get-Content -Path "tasks/in-flight.json" -Raw
        Write-Output ""
        Write-Output ""
    }

    # 3. progress
    if (Test-Path "tasks/progress.md") {
        Write-Output "### 3. 项目进度 (tasks/progress.md)"
        Get-Content -Path "tasks/progress.md" -TotalCount 20
        Write-Output ""
        Write-Output "..."
        Write-Output ""
    }

    # 4. feature-list - 提取 in_progress / blocked
    if (Test-Path "tasks/feature-list.json") {
        Write-Output "### 4. 功能清单 (tasks/feature-list.json) - 提取 in_progress/blocked 项"
        $content = Get-Content -Path "tasks/feature-list.json" -Raw
        try {
            $json = $content | ConvertFrom-Json
            $features = if ($json.features) { $json.features } else { $json }
            $filtered = $features | Where-Object { $_.status -in @("in_progress", "blocked") }
            if ($filtered.Count -gt 0) {
                $filtered | ConvertTo-Json -Depth 10
            } else {
                Write-Output "(没有 in_progress 或 blocked 项)"
            }
        } catch {
            $content -split "`n" | Select-String -Pattern '"status"\s*:\s*"(in_progress|blocked)"' -Context 2,2
        }
        Write-Output ""
    }
} else {
    Write-Output "## [项目级] 本项目还没有 tasks/ 目录"
    Write-Output "如果是新项目第一次开工，建议先建：mkdir tasks; ni tasks\session-handoff.md, tasks\progress.md"
    Write-Output ""
}

# ============================================================
# 全局跨项目记忆（~/.claude/memory/）
# ============================================================
$GlobalMemory = Join-Path $HOME ".claude/memory"

if (Test-Path $GlobalMemory) {
    Write-Output "## [全局] 跨项目长期经验 (~/.claude/memory/)"
    Write-Output ""

    # 5. 全局 lessons.md
    $lessonsPath = Join-Path $GlobalMemory "lessons.md"
    if (Test-Path $lessonsPath) {
        Write-Output "### 5. 全局避坑经验 (~/.claude/memory/lessons.md) - 最新 30 行"
        Get-Content -Path $lessonsPath -Tail 30
        Write-Output ""
    }

    # 6. 全局 user-preferences
    $prefsPath = Join-Path $GlobalMemory "user-preferences.md"
    if (Test-Path $prefsPath) {
        Write-Output "### 6. 用户长期偏好 (~/.claude/memory/user-preferences.md)"
        Get-Content -Path $prefsPath -Raw
        Write-Output ""
    }
} else {
    Write-Output "## [全局] 还没有全局 memory 目录"
    Write-Output "建议先建：mkdir ~/.claude/memory; ni ~/.claude/memory/lessons.md"
    Write-Output ""
}

Write-Output "--- [INJECTION END] ---"
Write-Output ""
Write-Output "[硬规则提醒]"
Write-Output "1. 优先基于以上上下文继续工作；不要从零开始猜测"
Write-Output "2. tasks/ 是项目级状态，只为当前项目维护"
Write-Output "3. memory/ 是跨项目长期经验，写入 ~/.claude/memory/lessons.md 让所有项目都受益"
Write-Output "4. 同类错误重复出现 → 必须写进 ~/.claude/memory/lessons.md（由 Stop hook 提醒）"
Write-Output "5. 如果 tasks/ 不存在且是新项目，先和用户确认本轮目标再动手"
