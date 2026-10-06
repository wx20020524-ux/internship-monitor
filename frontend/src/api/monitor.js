import { request } from "./client";

export function getMonitors() {
    return request("/api/monitors");
}

export function createMonitor(payload) {
    return request("/api/monitors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export function updateMonitor(id, payload) {
    return request(`/api/monitors/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export function deleteMonitor(id) {
    return request(`/api/monitors/${id}`, { method: "DELETE" });
}

export function runMonitor(id) {
    return request(`/api/monitors/${id}/run`, { method: "POST" });
}

export function getMonitorHits(id) {
    return request(`/api/monitors/${id}/hits`);
}

export function acknowledgeMonitor(id) {
    return request(`/api/monitors/${id}/ack`, { method: "POST" });
}
