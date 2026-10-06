from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from src.ai.resume_service import ResumeMatchService
from src.cache.redis import cache


router = APIRouter(prefix="/resume", tags=["简历匹配"])
service = ResumeMatchService()


@router.post("/match")
async def match_resume(
    file: UploadFile = File(...),
    x_user_id: str | None = Header(default=None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="请上传简历文件")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="只支持 PDF 和 DOCX 简历")

    file_data = await file.read()
    if not file_data:
        raise HTTPException(status_code=400, detail="上传的文件为空")
    if len(file_data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="简历文件不能超过 10MB")

    # Redis 限流：同一用户 60 秒最多 5 次，Redis 不可用时降级为不限制。
    user_id = (x_user_id or "default").strip()[:100] or "default"
    rate_key = f"resume-rate:{user_id}"
    count = cache.incr_with_ttl(rate_key, ttl=60)
    if count is not None and count > 5:
        raise HTTPException(status_code=429, detail="简历匹配请求过于频繁，请稍后再试")

    cache_key = service.cache_key_for_file(file_data)
    cached = service.get_cached_result(cache_key)
    if cached is not None:
        return {"success": True, "cached": True, **cached}

    temp_path = None
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(file_data)
            temp_path = temp_file.name

        result = service.match_resume(temp_path)
        service.cache_result(cache_key, result)
        return {"success": True, "cached": False, **result}

    except HTTPException:
        raise
    except Exception as error:
        print("简历匹配失败：", error)
        raise HTTPException(status_code=500, detail=f"简历匹配失败：{error}") from error
    finally:
        if temp_path:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
