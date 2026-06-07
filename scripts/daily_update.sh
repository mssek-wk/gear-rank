#!/bin/bash
# 器材榜每日自动更新：跑爬虫 → 有变化则提交并推送到 GitHub。
# 由 ~/Library/LaunchAgents/com.gearrank.daily.plist 定时调用。
# launchd 环境的 PATH 很精简，这里显式补齐并全部用绝对路径。

export PATH="$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
REPO="$HOME/Desktop/gear-rank"
LOG="$REPO/update.log"

cd "$REPO" || exit 1
{
  echo "===== $(date '+%F %T') 开始每日更新 ====="
  # GEARRANK_LIVE=1：让 amazon 适配器实时重抓真实评分/评价/畅销榜并刷新快照
  GEARRANK_LIVE=1 /usr/bin/python3 crawler/run.py || echo "!! 爬虫执行出错"

  if [ -n "$(/usr/bin/git status --porcelain)" ]; then
    /usr/bin/git add -A
    /usr/bin/git commit -m "chore: 每日自动更新 $(date +%F)"
    if /usr/bin/git push; then
      echo ">> 已推送 GitHub，公网站点将自动重新部署"
    else
      echo "!! 推送失败（检查网络 / gh 登录态）"
    fi
  else
    echo ">> 数据无变化，跳过提交"
  fi
  echo "===== $(date '+%F %T') 结束 ====="
  echo
} >> "$LOG" 2>&1
