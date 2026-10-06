import { useEffect, useState } from "react";
import { Button, Card, Form, Input, List, Modal, Popconfirm, Space, Switch, Tag, Typography, message } from "antd";
import { createMonitor, deleteMonitor, getMonitorHits, getMonitors, runMonitor, updateMonitor } from "../api/monitor";

const { Text, Title } = Typography;

const emptyForm = { name: "", company: "", city: "", keyword: "", job_type: "", enabled: true };

export default function MonitorPanel({ onViewJob }) {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    const [modalOpen, setModalOpen] = useState(false);
    const [form] = Form.useForm();
    const [runningId, setRunningId] = useState(null);
    const [hits, setHits] = useState({});

    const load = async () => {
        setLoading(true);
        try { setItems(await getMonitors()); }
        catch (error) { message.error(error.message || "监控加载失败"); }
        finally { setLoading(false); }
    };

    useEffect(() => { load(); }, []);

    const create = async () => {
        try {
            const values = await form.validateFields();
            await createMonitor(values);
            message.success("监控已创建");
            setModalOpen(false);
            form.resetFields();
            await load();
        } catch (error) {
            if (error?.errorFields) return;
            message.error(error.message || "创建监控失败");
        }
    };

    const toggle = async (item) => {
        try {
            await updateMonitor(item.id, { enabled: !item.enabled });
            await load();
        } catch (error) { message.error(error.message || "更新监控失败"); }
    };

    const remove = async (id) => {
        try { await deleteMonitor(id); await load(); }
        catch (error) { message.error(error.message || "删除监控失败"); }
    };

    const run = async (item) => {
        setRunningId(item.id);
        try {
            const data = await runMonitor(item.id);
            message.success(`本次发现 ${data.new_hits} 个新监控结果`);
            setHits((current) => ({ ...current, [item.id]: data.jobs || [] }));
            await load();
        } catch (error) { message.error(error.message || "监控执行失败"); }
        finally { setRunningId(null); }
    };

    const showHits = async (item) => {
        try {
            const hits = await getMonitorHits(item.id);
            setHits((current) => ({
                ...current,
                [item.id]: hits,
            }));
            }
        catch (error) { message.error(error.message || "告警加载失败"); }
    };

    return (
        <Card
            title="岗位监控"
            extra={<Button type="primary" onClick={() => { form.setFieldsValue(emptyForm); setModalOpen(true); }}>新建监控</Button>}
            loading={loading}
        >
            <Text type="secondary">监控 Worker 会按配置定期检查数据库中的新增/更新岗位；也可以点击“立即检查”手动触发。</Text>
            <List
                style={{ marginTop: 16 }}
                dataSource={items}
                locale={{ emptyText: "还没有配置监控" }}
                renderItem={(item) => (
                    <List.Item
                        key={item.id}
                        actions={[
                            <Button key="run" type="primary" loading={runningId === item.id} onClick={() => run(item)}>立即检查</Button>,
                            <Button key="hits" onClick={() => showHits(item)}>查看命中</Button>,
                            <Switch key="toggle" checked={!!item.enabled} onChange={() => toggle(item)} />,
                            <Popconfirm key="delete" title="确认删除这个监控？" onConfirm={() => remove(item.id)}><Button danger>删除</Button></Popconfirm>,
                        ]}
                    >
                        <Title level={5} style={{ margin: 0 }}>{item.name}</Title>
                        <Space size={8} wrap style={{ marginTop: 8 }}>
                            {item.company && <Tag>{item.company}</Tag>}
                            {item.city && <Tag>{item.city}</Tag>}
                            {item.job_type && <Tag>{item.job_type}</Tag>}
                            {item.keyword && <Tag color="blue">关键词：{item.keyword}</Tag>}
                            <Tag color={item.pending_count ? "red" : "default"}>待处理 {item.pending_count || 0}</Tag>
                        </Space>
                        {hits[item.id]?.length > 0 && (
                            <div className="monitor-hit-list">
                                {hits[item.id].slice(0, 5).map((hit) => (
                                    <Button key={hit.hit_id || hit.id} type="link" onClick={() => hit.id && onViewJob({ id: hit.id, title: hit.title, company: hit.company, city: hit.city, department: hit.department, job_type: hit.job_type, update_time: hit.update_time, source_url: hit.source_url })}>
                                        {hit.title}
                                    </Button>
                                ))}
                            </div>
                        )}
                    </List.Item>
                )}
            />

            <Modal title="新建岗位监控" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={create} okText="创建">
                <Form form={form} layout="vertical" initialValues={emptyForm}>
                    <Form.Item name="name" label="监控名称" rules={[{ required: true, message: "请输入监控名称" }]}>
                        <Input placeholder="例如：AI Agent 深圳实习" />
                    </Form.Item>
                    <div className="monitor-form-grid">
                        <Form.Item name="company" label="公司"><Input placeholder="腾讯" /></Form.Item>
                        <Form.Item name="city" label="城市"><Input placeholder="深圳" /></Form.Item>
                        <Form.Item name="job_type" label="岗位类型"><Input placeholder="实习" /></Form.Item>
                        <Form.Item name="keyword" label="关键词"><Input placeholder="Agent / RAG / Python" /></Form.Item>
                    </div>
                    <Form.Item name="enabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
                </Form>
            </Modal>
        </Card>
    );
}
