import { useCallback, useEffect, useState } from "react";
import { getCities, getCompanies, getJobTypes, getJobs } from "../api/jobs";

export function useJobs() {
    const [jobs, setJobs] = useState([]);
    const [total, setTotal] = useState(0);
    const [companies, setCompanies] = useState([]);
    const [cities, setCities] = useState([]);
    const [jobTypes, setJobTypes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [filters, setFilters] = useState({
        company: "",
        city: "",
        keyword: "",
        job_type: "",
        sort_order: "latest",
    });
    const [page, setPage] = useState(1);
    const pageSize = 20;

    const loadOptions = useCallback(async () => {
        const [companyData, cityData, typeData] = await Promise.all([
            getCompanies(),
            getCities(),
            getJobTypes(),
        ]);
        setCompanies(Array.isArray(companyData) ? companyData : []);
        setCities(Array.isArray(cityData) ? cityData : []);
        setJobTypes(Array.isArray(typeData) ? typeData : []);
    }, []);

    const loadJobs = useCallback(async (nextPage = page, nextFilters = filters) => {
        setLoading(true);
        try {
            const data = await getJobs({
                ...nextFilters,
                page: nextPage,
                page_size: pageSize,
            });
            setJobs(data.items || []);
            setTotal(data.total || 0);
            setPage(data.page || nextPage);
        } finally {
            setLoading(false);
        }
    }, [page, filters]);

    useEffect(() => {
        Promise.all([loadOptions(), loadJobs(1)]).catch(() => {
            // App displays a message from caller when needed.
        });
    }, [loadOptions]);

    const search = useCallback((nextFilters) => {
        setFilters(nextFilters);
        setPage(1);
        return loadJobs(1, nextFilters);
    }, [loadJobs]);

    const changePage = useCallback((nextPage) => {
        setPage(nextPage);
        return loadJobs(nextPage, filters);
    }, [filters, loadJobs]);

    return {
        jobs, total, companies, cities, jobTypes,
        loading, filters, setFilters, page, pageSize,
        loadJobs, search, changePage,
    };
}
