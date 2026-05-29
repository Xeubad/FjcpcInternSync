#!/bin/bash
# .claude/hooks/start.sh
# 用途：会话开始时自动注入 tasks/（项目级） + memory/（全局）上下文
# 分层：
#   tasks/      → 项目本地，每个项目独立（功能进度、handoff、in-flight）
#   memory/     → 全局 ~/.claude/memory/，跨项目共享（lessons、长期偏好）
# 适用：macOS / Linux 原生 bash；Windows Git Bash
# 部署：复制到 .claude/hooks/start.sh 并 chmod +x

set -e

echo "--- [SESSION START CONTEXT INJECTION] ---"
echo ""

# ============================================================
# 项目级任务运行态（tasks/ 在项目根）
# ============================================================
if [ -d "tasks" ]; then
    echo "## [项目级] 当前项目运行态 (./tasks/)"
    echo ""

    # 1. handoff —— 上次交接（最优先）
    if [ -f "tasks/session-handoff.md" ]; then
        echo "### 1. 上次任务交接 (tasks/session-handoff.md)"
        head -n 30 tasks/session-handoff.md
        echo ""
        echo "..."
        echo ""
    fi

    # 2. in-flight —— 当前进行中
    if [ -f "tasks/in-flight.json" ]; then
        echo "### 2. 当前进行中的任务 (tasks/in-flight.json)"
        cat tasks/in-flight.json
        echo ""
        echo ""
    fi

    # 3. progress —— 项目进度
    if [ -f "tasks/progress.md" ]; then
        echo "### 3. 项目进度 (tasks/progress.md)"
        head -n 20 tasks/progress.md
        echo ""
        echo "..."
        echo ""
    fi

    # 4. feature-list —— 提取 in_progress / blocked 项
    if [ -f "tasks/feature-list.json" ]; then
        echo "### 4. 功能清单 (tasks/feature-list.json) - 提取 in_progress/blocked 项"
        grep -E '"status":\s*"(in_progress|blocked)"' tasks/feature-list.json -B 2 -A 2 || echo "(没有 in_progress 或 blocked 项)"
        echo ""
    fi
else
    echo "## [项目级] 本项目还没有 tasks/ 目录"
    echo "如果是新项目第一次开工，建议先建：mkdir -p tasks && touch tasks/session-handoff.md tasks/progress.md"
    echo ""
fi

# ============================================================
# 全局跨项目记忆（~/.claude/memory/）
# ============================================================
GLOBAL_MEMORY="$HOME/.claude/memory"

if [ -d "$GLOBAL_MEMORY" ]; then
    echo "## [全局] 跨项目长期经验 (~/.claude/memory/)"
    echo ""

    # 5. 全局 lessons.md（最重要）
    if [ -f "$GLOBAL_MEMORY/lessons.md" ]; then
        echo "### 5. 全局避坑经验 (~/.claude/memory/lessons.md) - 最新 30 行"
        tail -n 30 "$GLOBAL_MEMORY/lessons.md"
        echo ""
    fi

    # 6. 全局 user-preferences（如有）
    if [ -f "$GLOBAL_MEMORY/user-preferences.md" ]; then
        echo "### 6. 用户长期偏好 (~/.claude/memory/user-preferences.md)"
        cat "$GLOBAL_MEMORY/user-preferences.md"
        echo ""
    fi
else
    echo "## [全局] 还没有全局 memory 目录"
    echo "建议先建：mkdir -p ~/.claude/memory && touch ~/.claude/memory/lessons.md"
    echo ""
fi

echo "--- [INJECTION END] ---"
echo ""
echo "[硬规则提醒]"
echo "1. 优先基于以上上下文继续工作；不要从零开始猜测"
echo "2. tasks/ 是项目级状态，只为当前项目维护"
echo "3. memory/ 是跨项目长期经验，写入 ~/.claude/memory/lessons.md 让所有项目都受益"
echo "4. 同类错误重复出现 → 必须写进 ~/.claude/memory/lessons.md（由 Stop hook 提醒）"
echo "5. 如果 tasks/ 不存在且是新项目，先和用户确认本轮目标再动手"
