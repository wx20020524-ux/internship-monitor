import { useEffect, useState } from "react";
import { Alert, Button, Card, Divider, Progress, Space, Tag, Typography, Upload, message } from "antd";
import { buildEmbeddingIndex, getEmbeddingStatus } from "../api/ai";
import { matchResume } from "../api/resume";
import { getJobDetail } from "../api/jobs";

const { Paragraph, Text, Title } = Typography;

export default function ResumeMatcher({ onViewJob }) {
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [indexing, setIndexing] = useState(false);
    const [embeddingStatus, setEmbeddingStatus] = useState(null);

    const loadEmbeddingStatus = async () => {
        try {
            setEmbeddingStatus(await getEmbeddingStatus());
        } catch (error) {
            console.error(error);
        }
    };

    useEffect(() => { loadEmbeddingStatus(); }, []);

    const handleMatch = async () => {
        if (!file) {
            message.warning("请先选择 PDF 或 DOCX 简历");
            return;
        }
        setLoading(true);
        try {
            const data = await matchResume(file);
            setResult(data);
            message.success(data.cached ? "已从缓存返回匹配结果" : "AI 匹配完成");
        } catch (error) {
            message.error(error.message || "简历匹配失败");
        } finally {
            setLoading(false);
        }
    };

    const handleIndex = async () => {
        setIndexing(true);
        try {
            const data = await buildEmbeddingIndex(200);
            message.success(`语义索引更新完成：${data.indexed} 条`);
            await loadEmbeddingStatus();
        } catch (error) {
            message.error(error.message || "构建 Embedding 索引失败");
        } finally {
            setIndexing(false);
        }
    };

    return (
        <div className="ai-layout">
            <Card title="AI 简历智能匹配" className="ai-upload-card">
                <Upload
                    beforeUpload={(selectedFile) => {
                        setFile(selectedFile);
                        return false;
                    }}
                    maxCount={1}
                    accept=".pdf,.docx"
                    onRemove={() => setFile(null)}
                >
                    <Button size="large">选择 PDF / DOCX 简历</Button>
                </Upload>
                <Text type="secondary" style={{ display: "block", marginTop: 12 }}>
                    规则粗筛 + 语义召回 + Qwen 精排；相同简历会优先读取 Redis 缓存。
                </Text>
                <Space style={{ marginTop: 18 }}>
                    <Button type="primary" loading={loading} onClick={handleMatch}>开始智能匹配</Button>
                    <Button loading={indexing} onClick={handleIndex}>更新 Embedding 索引</Button>
                </Space>
                {embeddingStatus && (
                    <div className="index-status">
                        <Text type="secondary">
                            语义索引：{embeddingStatus.indexed_jobs}/{embeddingStatus.total_jobs} 条，{embeddingStatus.model} · {embeddingStatus.dimension} 维
                        </Text>
                    </div>
                )}
            </Card>

            {result?.profile && (
                <Card title="简历画像">
                    <Space wrap>
                        {(result.profile.target_roles || []).map((item) => <Tag key={item} color="blue">{item}</Tag>)}
                        {(result.profile.skills || []).slice(0, 12).map((item) => <Tag key={item}>{item}</Tag>)}
                    </Space>
                    {result.profile.education && <Paragraph style={{ marginTop: 12 }}>{result.profile.education}</Paragraph>}
                </Card>
            )}

            {result?.recommendations?.length > 0 && (
                <Card title={`推荐岗位 Top ${result.recommendations.length}`}>
                    <Alert
                        type={result.semantic_enabled ? "success" : "info"}
                        showIcon
                        message={result.semantic_enabled ? "已启用 Embedding 语义召回" : "当前使用规则召回，构建语义索引后可启用 Embedding"}
                        style={{ marginBottom: 16 }}
                    />
                    <div className="recommendation-list">
                        {result.recommendations.map((item) => (
                            <div className="recommendation-row" key={item.id || `${item.company}-${item.title}`}>
                                <div className="recommendation-main">
                                    <Title level={5} style={{ margin: 0 }}>{item.title}</Title>
                                    <Text type="secondary">{item.company} · {item.city || "地点不限"}</Text>
                                    <Space wrap style={{ marginTop: 8 }}>
                                        {(item.matched_skills || []).slice(0, 6).map((skill) => <Tag key={skill} color="green">✓ {skill}</Tag>)}
                                        {(item.missing_skills || []).slice(0, 4).map((skill) => <Tag key={skill} color="red">缺少 {skill}</Tag>)}
                                    </Space>
                                    <div className="score-breakdown">
                                        <Text type="secondary">规则 {item.rule_score ?? 0}</Text>
                                        <Text type="secondary">Qwen {item.llm_score ?? 0}</Text>
                                        {item.semantic_score > 0 && <Text type="secondary">语义 {item.semantic_score}</Text>}
                                    </div>
                                    {item.reason && <Paragraph ellipsis={{ rows: 2 }} style={{ margin: "8px 0 0" }}>{item.reason}</Paragraph>}
                                </div>
                                <div className="recommendation-score">
                                    <Progress type="circle" size={58} percent={item.match_score} format={(value) => `${value}`} />
                                    <Button type="link" onClick={async () => {
                                        if (!item.id) return;
                                        try { onViewJob(await getJobDetail(item.id)); } catch (error) { message.error(error.message); }
                                    }}>查看岗位</Button>
                                </div>
                            </div>
                        ))}
                    </div>
                </Card>
            )}
        </div>
    );
}
