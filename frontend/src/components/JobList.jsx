import { Button, Empty, List, Space, Tag, Typography } from "antd";

const { Text, Title } = Typography;

function formatTime(value) {
    if (!value) return "暂无";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

export default function JobList({ jobs, total, loading, page, pageSize, onPageChange, onViewDetail, onToggleFavorite }) {
    return (
        <List
            loading={loading}
            itemLayout="vertical"
            pagination={total > pageSize ? {
                current: page,
                pageSize,
                total,
                onChange: onPageChange,
                showSizeChanger: false,
                align: "center",
                style: { marginTop: 24 },
            } : false}
            locale={{ emptyText: <Empty description="没有找到符合条件的岗位" /> }}
            dataSource={jobs}
            renderItem={(job) => (
                <List.Item
                    className="job-row"
                    key={job.id}
                    actions={[
                        <Button key="favorite" type={job.is_favorite ? "primary" : "default"} ghost={job.is_favorite} onClick={() => onToggleFavorite(job)}>
                            {job.is_favorite ? "★ 已收藏" : "☆ 收藏"}
                        </Button>,
                        <Button key="detail" type="primary" onClick={() => onViewDetail(job.id)}>查看详情</Button>,
                    ]}
                >
                    <div className="job-row-main">
                        <div className="job-row-title">
                            <div>
                                <Title level={4} style={{ margin: 0 }}>{job.title || "未命名岗位"}</Title>
                                <Space size={8} wrap style={{ marginTop: 10 }}>
                                    <Tag>{job.company || "未知公司"}</Tag>
                                    {job.city && <Tag>{job.city}</Tag>}
                                    {job.job_type && <Tag>{job.job_type}</Tag>}
                                    {job.category && <Tag>{job.category}</Tag>}
                                </Space>
                            </div>
                            <div className="job-row-meta">
                                <Text type="secondary">最近更新</Text>
                                <Text strong>{formatTime(job.update_time || job.publish_time)}</Text>
                            </div>
                        </div>

                        <div className="job-row-info">
                            <Text>{job.department || "暂无部门"}</Text>
                            <Text type="secondary">{job.education || "学历不限"}</Text>
                            <Text type="secondary">{job.experience || "经验不限"}</Text>
                            {job.salary && <Text type="secondary">{job.salary}</Text>}
                        </div>

                        <Typography.Paragraph ellipsis={{ rows: 2 }} className="job-row-desc">
                            {job.description || job.requirements || "暂无岗位描述"}
                        </Typography.Paragraph>
                        <Text type="secondary">来源：{job.source || "招聘官网"}</Text>
                    </div>
                </List.Item>
            )}
        />
    );
}
