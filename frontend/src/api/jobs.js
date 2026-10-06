import { request } from "./client";

export async function getJobs(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
            query.append(key, value);
        }
    });
    return request(`/api/jobs?${query.toString()}`);
}

export function getCompanies() {
    return request("/api/companies");
}

export function getCities() {
    return request("/api/cities");
}

export function getJobTypes() {
    return request("/api/job-types");
}

export function getJobDetail(jobId) {
    return request(`/api/jobs/${jobId}`);
}
