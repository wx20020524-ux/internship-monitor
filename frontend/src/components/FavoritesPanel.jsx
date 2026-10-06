import { useEffect, useState } from "react";
import { Button, Card, Empty, List, Space, Tag, Typography, message } from "antd";
import { getFavorites, removeFavorite } from "../api/favorites";

const { Text, Title } = Typography;

export default function FavoritesPanel({ onViewJob }) {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);

    const load = async () => {
        setLoading(true);
        try { setItems(await getFavorites()); }
        catch (error) { message.error(error.message || "收藏加载失败"); }
        finally { setLoading(false); }
    };

    useEffect(() => { load(); }, []);

    const remove = async (jobId) => {
        try {
            await removeFavorite(jobId);
            setItems((current) => current.filter((item) => item.id !== jobId));
        } catch (error) { message.error(error.message || "取消收藏失败"); }
    };

    return (
        <Card title={`我的收藏（${items.length}）`} loading={loading}>
            {items.length === 0 ? <Empty description="还没有收藏岗位" /> : (
                <List
                    itemLayout="vertical"
                    dataSource={items}
                    renderItem={(job) => (
                        <List.Item
                            key={job.id}
                            actions={[
                                <Button key="detail" type="primary" onClick={() => onViewJob(job)}>查看详情</Button>,
                                <Button key="remove" onClick={() => remove(job.id)}>取消收藏</Button>,
                            ]}
                        >
                            <Title level={5} style={{ margin: 0 }}>{job.title}</Title>
                            <Space size={8} wrap style={{ marginTop: 8 }}>
                                <Tag>{job.company}</Tag>
                                {job.city && <Tag>{job.city}</Tag>}
                                {job.job_type && <Tag>{job.job_type}</Tag>}
                            </Space>
                            <Text type="secondary">{job.department || "暂无部门"}</Text>
                        </List.Item>
                    )}
                />
            )}
        </Card>
    );
}
