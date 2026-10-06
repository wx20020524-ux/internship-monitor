from fastapi import APIRouter, Header, HTTPException

from src.api.schemas import MonitorCreate, MonitorResponse, MonitorRunResponse, MonitorUpdate
from src.db.monitor import (
    create_monitor,
    delete_monitor,
    find_matching_jobs,
    get_monitor,
    list_monitor_hits,
    list_monitors,
    mark_hits_notified,
    record_hits,
    update_monitor,
    update_monitor_checked_at,
)


router = APIRouter(prefix="/monitors", tags=["岗位监控"])


def _user_id(x_user_id: str | None) -> str:
    value = (x_user_id or "default").strip()
    return value[:100] or "default"


@router.get("", response_model=list[MonitorResponse])
def monitors(x_user_id: str | None = Header(default=None)):
    return list_monitors(_user_id(x_user_id))


@router.post("", response_model=MonitorResponse)
def create_monitor_config(payload: MonitorCreate, x_user_id: str | None = Header(default=None)):
    return create_monitor(_user_id(x_user_id), payload.model_dump())


@router.patch("/{monitor_id}", response_model=MonitorResponse)
def patch_monitor(
    monitor_id: int,
    payload: MonitorUpdate,
    x_user_id: str | None = Header(default=None),
):
    current = get_monitor(_user_id(x_user_id), monitor_id)
    if current is None:
        raise HTTPException(status_code=404, detail="监控不存在")
    data = {key: value for key, value in payload.model_dump().items() if value is not None}
    merged = {**current, **data}
    return update_monitor(_user_id(x_user_id), monitor_id, merged)


@router.delete("/{monitor_id}")
def remove_monitor(monitor_id: int, x_user_id: str | None = Header(default=None)):
    if not delete_monitor(_user_id(x_user_id), monitor_id):
        raise HTTPException(status_code=404, detail="监控不存在")
    return {"success": True}


@router.post("/{monitor_id}/run", response_model=MonitorRunResponse)
def run_monitor(monitor_id: int, x_user_id: str | None = Header(default=None)):
    user_id = _user_id(x_user_id)
    monitor = get_monitor(user_id, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=404, detail="监控不存在")
    jobs = find_matching_jobs(monitor, monitor.get("last_checked_at"))
    new_hits = record_hits(monitor_id, jobs)
    update_monitor_checked_at(monitor_id)
    return {"monitor_id": monitor_id, "new_hits": new_hits, "jobs": jobs[:50]}


@router.get("/{monitor_id}/hits")
def monitor_hits(
    monitor_id: int,
    limit: int = 50,
    x_user_id: str | None = Header(default=None),
):
    user_id = _user_id(x_user_id)
    if get_monitor(user_id, monitor_id) is None:
        raise HTTPException(status_code=404, detail="监控不存在")
    return list_monitor_hits(user_id, monitor_id, limit)


@router.post("/{monitor_id}/ack")
def acknowledge_monitor(monitor_id: int, x_user_id: str | None = Header(default=None)):
    user_id = _user_id(x_user_id)
    if get_monitor(user_id, monitor_id) is None:
        raise HTTPException(status_code=404, detail="监控不存在")
    return {"updated": mark_hits_notified(user_id, monitor_id)}
