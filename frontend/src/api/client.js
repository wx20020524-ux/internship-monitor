const USER_ID_KEY = "internship-monitor:user-id";

export function getUserId() {
    let userId = localStorage.getItem(USER_ID_KEY);
    if (!userId) {
        userId = crypto.randomUUID?.() || `local-${Date.now()}`;
        localStorage.setItem(USER_ID_KEY, userId);
    }
    return userId;
}

export async function request(url, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("X-User-Id", getUserId());

    const response = await fetch(url, {
        ...options,
        headers,
    });

    if (!response.ok) {
        let message = `请求失败：${response.status}`;
        try {
            const data = await response.json();
            if (data.detail) {
                message = typeof data.detail === "string"
                    ? data.detail
                    : JSON.stringify(data.detail);
            }
        } catch {
            // keep default message
        }
        throw new Error(message);
    }

    return response.json();
}
