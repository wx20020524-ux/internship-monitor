import { Button, Card, Input, Select, Space } from "antd";

export default function SearchPanel({ filters, companies, cities, jobTypes, onChange, onSearch, loading }) {
    return (
        <Card className="search-panel">
            <div className="search-grid">
                <Input
                    size="large"
                    placeholder="搜索岗位、技能、JD 关键词，例如 Agent / RAG / Python"
                    value={filters.keyword}
                    onChange={(event) => onChange({ ...filters, keyword: event.target.value })}
                    onPressEnter={onSearch}
                />
                <Select
                    size="large"
                    value={filters.company || undefined}
                    allowClear
                    placeholder="公司"
                    options={companies.map((item) => ({ label: item, value: item }))}
                    onChange={(value) => onChange({ ...filters, company: value || "" })}
                />
                <Select
                    size="large"
                    value={filters.city || undefined}
                    allowClear
                    placeholder="城市"
                    options={cities.map((item) => ({ label: item, value: item }))}
                    onChange={(value) => onChange({ ...filters, city: value || "" })}
                />
                <Select
                    size="large"
                    value={filters.job_type || undefined}
                    allowClear
                    placeholder="岗位类型"
                    options={jobTypes.map((item) => ({ label: item, value: item }))}
                    onChange={(value) => onChange({ ...filters, job_type: value || "" })}
                />
            </div>
            <div className="search-footer">
                <Select
                    value={filters.sort_order}
                    options={[{ label: "最新更新", value: "latest" }, { label: "最早更新", value: "earliest" }]}
                    onChange={(value) => onChange({ ...filters, sort_order: value })}
                />
                <Space>
                    <Button onClick={() => onChange({ company: "", city: "", keyword: "", job_type: "", sort_order: "latest" })}>
                        重置
                    </Button>
                    <Button type="primary" loading={loading} onClick={onSearch}>
                        搜索岗位
                    </Button>
                </Space>
            </div>
        </Card>
    );
}
