import { request } from "./client";

export function getEmbeddingStatus() {
    return request("/api/ai/embeddings/status");
}

export function buildEmbeddingIndex(limit = 200) {
    return request("/api/ai/embeddings/index", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit }),
    });
}
