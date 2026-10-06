import { Button, Descriptions, Empty, Modal, Spin, Tag, Typography } from "antd";

const { Paragraph, Title } = Typography;

export default function JobDetailModal({ open, loading, job, onClose, onToggleFavorite }) {
    return (
        <Modal
            open={open}
            title={job?.title || "岗位详情"}
            width={900}
            onCancel={onClose}
            footer={job ? [
                <Button key="favorite" onClick={() => onToggleFavorite(job)}>
                    {job.is_favorite ? "★ 取消收藏" : "☆ 收藏岗位"}
                </Button>,
                <Button key="official" type="primary" href={job.source_url || undefined} target="_blank" rel="noreferrer" disabled={!job.source_url}>
                    查看官方页面
                </Button>,
                <Button key="close" onClick={onClose}>关闭</Button>,
            ] : [<Button key="close" onClick={onClose}>关闭</Button>]}
        >
            {loading ? (
                <div className="modal-loading"><Spin size="large" /></div>
            ) : job ? (
                <>
                    <Descriptions bordered column={2} size="small">
                        <Descriptions.Item label="公司">{job.company || "-"}</Descriptions.Item>
                        <Descriptions.Item label="城市">{job.city || "-"}</Descriptions.Item>
                        <Descriptions.Item label="部门">{job.department || "-"}</Descriptions.Item>
                        <Descriptions.Item label="岗位类型">{job.job_type || "-"}</Descriptions.Item>
                        <Descriptions.Item label="学历">{job.education || "-"}</Descriptions.Item>
                        <Descriptions.Item label="经验">{job.experience || "-"}</Descriptions.Item>
                        <Descriptions.Item label="薪资">{job.salary || "-"}</Descriptions.Item>
                        <Descriptions.Item label="来源">{job.source || "-"}</Descriptions.Item>
                    </Descriptions>

                    <Title level={5}>岗位描述</Title>
                    <Paragraph>{job.description || "暂无岗位描述"}</Paragraph>

                    <Title level={5}>任职要求</Title>
                    <Paragraph>{job.requirements || "暂无任职要求"}</Paragraph>

                    {job.category && <><Title level={5}>岗位分类</Title><Tag>{job.category}</Tag></>}
                </>
            ) : <Empty description="暂无岗位详情" />}
        </Modal>
    );
}
