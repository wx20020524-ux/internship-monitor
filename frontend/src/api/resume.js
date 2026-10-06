const API_BASE_URL = "/api";

import { getUserId } from "./client";

export async function matchResume(file) {
    if (!file) throw new Error("请选择简历文件");

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/resume/match`, {
        method: "POST",
        headers: { "X-User-Id": getUserId() },
        body: formData,
    });

    if (!response.ok) {
        let message = "简历匹配失败";
        try {
            const data = await response.json();
            if (data.detail) {
                message = typeof data.detail === "string"
                    ? data.detail
                    : JSON.stringify(data.detail);
            }
        } catch {
            // use fallback
        }
        throw new Error(message);
    }

    return response.json();
}
