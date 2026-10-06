import { request } from "./client";

export function getFavorites() {
    return request("/api/favorites");
}

export function addFavorite(jobId) {
    return request(`/api/favorites/${jobId}`, { method: "POST" });
}

export function removeFavorite(jobId) {
    return request(`/api/favorites/${jobId}`, { method: "DELETE" });
}

export function toggleFavorite(jobId, active) {
    return active ? removeFavorite(jobId) : addFavorite(jobId);
}
