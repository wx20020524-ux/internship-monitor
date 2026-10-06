import os
import time
from datetime import datetime

from dotenv import load_dotenv

from src.db.monitor import (
    find_matching_jobs,
    list_enabled_monitors,
    record_hits,
    update_monitor_checked_at,
)
from src.db.schema import ensure_schema

load_dotenv()

INTERVAL_SECONDS = max(30, int(os.getenv("MONITOR_INTERVAL_SECONDS", "300")))


def run_cycle() -> int:
    total_hits = 0
    for monitor in list_enabled_monitors():
        try:
            jobs = find_matching_jobs(monitor, monitor.get("last_checked_at"))
            total_hits += record_hits(monitor["id"], jobs)
            update_monitor_checked_at(monitor["id"], datetime.now())
            if jobs:
                print(
                    f"[monitor] {monitor['name']} -> "
                    f"发现 {len(jobs)} 个匹配岗位，新增告警 {total_hits}"
                )
        except Exception as error:
            print(f"[monitor] {monitor.get('name', monitor.get('id'))} 执行失败：{error}")
    return total_hits


def main() -> None:
    ensure_schema()
    print(f"岗位监控 Worker 已启动，轮询间隔：{INTERVAL_SECONDS}s")
    while True:
        try:
            run_cycle()
        except Exception as error:
            print(f"[monitor] 本轮执行失败：{error}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
