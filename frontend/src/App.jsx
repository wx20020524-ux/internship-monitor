import { useCallback, useState } from "react";
import { App as AntApp, Card, Layout, Space, Statistic, Tabs, Tag, Typography, message } from "antd";

import { addFavorite, removeFavorite } from "./api/favorites";
import { getJobDetail } from "./api/jobs";
import { useJobs } from "./hooks/useJobs";
import FavoritesPanel from "./components/FavoritesPanel";
import JobDetailModal from "./components/JobDetailModal";
import JobList from "./components/JobList";
import MonitorPanel from "./components/MonitorPanel";
import ResumeMatcher from "./components/ResumeMatcher";
import SearchPanel from "./components/SearchPanel";

const { Header, Content } = Layout;
const { Title, Text } = Typography;

function App() {
    const {
        jobs,
        total,
        companies,
        cities,
        jobTypes,
        loading,
        filters,
        setFilters,
        page,
        pageSize,
        search,
        changePage,
        loadJobs,
    } = useJobs();

    const [detailOpen, setDetailOpen] = useState(false);
    const [detailLoading, setDetailLoading] = useState(false);
    const [selectedJob, setSelectedJob] = useState(null);

    const viewJob = useCallback(async (jobOrId) => {
        const jobId = typeof jobOrId === "object" ? jobOrId.id : jobOrId;
        if (!jobId) return;
        setDetailOpen(true);
        setDetailLoading(true);
        setSelectedJob(null);
        try {
            setSelectedJob(await getJobDetail(jobId));
        } catch (error) {
            message.error(error.message || "岗位详情加载失败");
            setDetailOpen(false);
        } finally {
            setDetailLoading(false);
        }
    }, []);

    const toggleFavorite = useCallback(async (job) => {
        try {
            if (job.is_favorite) {
                await removeFavorite(job.id);
            } else {
                await addFavorite(job.id);
            }
            const nextFavorite = !job.is_favorite;
            setSelectedJob((current) => current?.id === job.id ? { ...current, is_favorite: nextFavorite } : current);
            await loadJobs(page);
            message.success(nextFavorite ? "已加入收藏" : "已取消收藏");
        } catch (error) {
            message.error(error.message || "收藏操作失败");
        }
    }, [loadJobs, page]);

    return (
        <AntApp>
            <Layout className="app-layout">
                <Header className="app-header">
                    <div className="header-inner">
                        <div>
                            <Title level={3} style={{ margin: 0, color: "#fff" }}>AI 实习信息平台</Title>
                            <Text style={{ color: "rgba(255,255,255,.7)" }}>岗位搜索 · 简历匹配 · 收藏 · 岗位监控</Text>
                        </div>
                        <Tag color="blue">v2.0 AI</Tag>
                    </div>
                </Header>

                <Content className="app-content">
                    <div className="stats-grid">
                        <Card><Statistic title="搜索结果" value={total} suffix="个" /></Card>
                        <Card><Statistic title="公司" value={companies.length} suffix="家" /></Card>
                        <Card><Statistic title="覆盖城市" value={cities.length} suffix="个" /></Card>
                        <Card><Statistic title="岗位类型" value={jobTypes.length} suffix="类" /></Card>
                    </div>

                    <Tabs
                        defaultActiveKey="jobs"
                        items={[
                            {
                                key: "jobs",
                                label: "岗位大厅",
                                children: (
                                    <Space direction="vertical" size={16} style={{ width: "100%" }}>
                                        <SearchPanel
                                            filters={filters}
                                            companies={companies}
                                            cities={cities}
                                            jobTypes={jobTypes}
                                            onChange={setFilters}
                                            onSearch={() => search(filters)}
                                            loading={loading}
                                        />
                                        <Card title={<span>岗位列表 <Text type="secondary">共 {total} 条</Text></span>}>
                                            <JobList
                                                jobs={jobs}
                                                total={total}
                                                loading={loading}
                                                page={page}
                                                pageSize={pageSize}
                                                onPageChange={changePage}
                                                onViewDetail={viewJob}
                                                onToggleFavorite={toggleFavorite}
                                            />
                                        </Card>
                                    </Space>
                                ),
                            },
                            {
                                key: "ai",
                                label: "AI 智能推荐",
                                children: <ResumeMatcher onViewJob={viewJob} />,
                            },
                            {
                                key: "favorites",
                                label: "我的收藏",
                                children: <FavoritesPanel onViewJob={viewJob} />,
                            },
                            {
                                key: "monitor",
                                label: "岗位监控",
                                children: <MonitorPanel onViewJob={viewJob} />,
                            },
                        ]}
                    />
                </Content>
            </Layout>

            <JobDetailModal
                open={detailOpen}
                loading={detailLoading}
                job={selectedJob}
                onClose={() => setDetailOpen(false)}
                onToggleFavorite={toggleFavorite}
            />
        </AntApp>
    );
}

export default App;
