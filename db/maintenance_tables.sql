-- 养老 AI 系统数据维护模块
-- 新增表和相关对象

-- ==================== 1. 每日摘要表 ====================

CREATE TABLE IF NOT EXISTS daily_summaries (
    id SERIAL PRIMARY KEY,
    summary_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    elder_id VARCHAR(50) NOT NULL,
    family_id VARCHAR(50) NOT NULL,
    summary_date DATE NOT NULL,

    -- 活动指标
    total_activity_minutes INTEGER DEFAULT 0,
    active_rooms JSONB DEFAULT '[]'::jsonb,
    room_activity_distribution JSONB DEFAULT '{}'::jsonb,

    -- 睡眠指标
    sleep_start_time TIME,
    sleep_end_time TIME,
    sleep_quality_score NUMERIC(3,2) DEFAULT 0,

    -- 卫生间指标
    bathroom_visits INTEGER DEFAULT 0,
    avg_bathroom_duration_minutes NUMERIC(5,2) DEFAULT 0,
    abnormal_bathroom_visits INTEGER DEFAULT 0,

    -- 告警指标
    total_alerts INTEGER DEFAULT 0,
    critical_alerts INTEGER DEFAULT 0,
    warning_alerts INTEGER DEFAULT 0,

    -- 基线对比
    activity_baseline_variance NUMERIC(5,2) DEFAULT 0,
    pattern_deviation_count INTEGER DEFAULT 0,

    -- 数据质量
    data_quality_score NUMERIC(3,2) DEFAULT 0,
    device_uptime_percent NUMERIC(5,2) DEFAULT 0,

    -- 备注和建议
    notes TEXT,
    recommendations JSONB DEFAULT '[]'::jsonb,

    -- 系统字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_daily_summaries_elder FOREIGN KEY (elder_id) REFERENCES elders(elder_id),
    CONSTRAINT fk_daily_summaries_family FOREIGN KEY (family_id) REFERENCES families(family_id),
    UNIQUE(elder_id, family_id, summary_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_summary_elder_date
    ON daily_summaries(elder_id, summary_date DESC);

CREATE INDEX IF NOT EXISTS idx_daily_summary_family_date
    ON daily_summaries(family_id, summary_date DESC);

-- ==================== 2. 告警反馈表 ====================

CREATE TABLE IF NOT EXISTS alert_feedback (
    id SERIAL PRIMARY KEY,
    feedback_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    alert_id UUID NOT NULL,
    elder_id VARCHAR(50) NOT NULL,
    family_id VARCHAR(50) NOT NULL,

    -- 反馈信息
    feedback_type VARCHAR(50) NOT NULL,  -- 'true_positive', 'false_positive', 'delayed', 'missed'
    feedback_confidence NUMERIC(3,2),     -- 反馈的可信度 (0-1)
    severity_assessment VARCHAR(50),      -- 'correct', 'overestimated', 'underestimated'

    -- 用户反馈
    user_id VARCHAR(100),
    feedback_text TEXT,
    action_taken VARCHAR(50),             -- 'none', 'monitored', 'contacted', 'hospitalized'

    -- 后续情况
    outcome VARCHAR(50),                  -- 'recovered', 'ongoing', 'hospitalized', 'resolved'
    follow_up_date DATE,
    follow_up_notes TEXT,

    -- 系统字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_alert_feedback_elder FOREIGN KEY (elder_id) REFERENCES elders(elder_id),
    CONSTRAINT fk_alert_feedback_family FOREIGN KEY (family_id) REFERENCES families(family_id),
    CONSTRAINT fk_alert_feedback_alert FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);

CREATE INDEX IF NOT EXISTS idx_alert_feedback_alert_id
    ON alert_feedback(alert_id);

CREATE INDEX IF NOT EXISTS idx_alert_feedback_elder_date
    ON alert_feedback(elder_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_alert_feedback_type
    ON alert_feedback(feedback_type);

-- ==================== 3. 数据保留日志表 ====================

CREATE TABLE IF NOT EXISTS data_retention_logs (
    id SERIAL PRIMARY KEY,
    log_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    operation_type VARCHAR(50) NOT NULL,  -- 'archive', 'delete', 'backup'
    table_name VARCHAR(100) NOT NULL,
    retention_days INTEGER,
    rows_affected INTEGER DEFAULT 0,
    start_date DATE,
    end_date DATE,
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'completed', 'failed'
    error_message TEXT,
    executed_at TIMESTAMP,
    duration_seconds INTEGER,
    backup_file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_retention_logs_date
    ON data_retention_logs(created_at DESC);

-- ==================== 4. 定时任务执行日志 ====================

CREATE TABLE IF NOT EXISTS scheduled_task_logs (
    id SERIAL PRIMARY KEY,
    task_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    task_name VARCHAR(100) NOT NULL,     -- 'generate_daily_summary', 'update_patterns', 'cleanup_events'
    elder_id VARCHAR(50),
    family_id VARCHAR(50),

    status VARCHAR(50) NOT NULL,         -- 'scheduled', 'running', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    records_processed INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    error_message TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_logs_name_date
    ON scheduled_task_logs(task_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_task_logs_status
    ON scheduled_task_logs(status);

-- ==================== 5. 触发器 ====================

-- 自动更新 daily_summaries updated_at
CREATE TRIGGER update_daily_summaries_timestamp
    BEFORE UPDATE ON daily_summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 自动更新 alert_feedback updated_at
CREATE TRIGGER update_alert_feedback_timestamp
    BEFORE UPDATE ON alert_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==================== 6. 视图 ====================

-- 视图：每日摘要统计（按家庭）
CREATE OR REPLACE VIEW v_daily_summary_stats AS
SELECT
    ds.family_id,
    ds.summary_date,
    COUNT(DISTINCT ds.elder_id) as elder_count,
    AVG(ds.total_activity_minutes) as avg_activity_minutes,
    AVG(ds.sleep_quality_score) as avg_sleep_quality,
    SUM(ds.total_alerts) as total_alerts_today,
    SUM(ds.critical_alerts) as critical_alerts_today,
    AVG(ds.data_quality_score) as avg_data_quality
FROM daily_summaries ds
GROUP BY ds.family_id, ds.summary_date;

-- 视图：告警反馈统计
CREATE OR REPLACE VIEW v_alert_feedback_stats AS
SELECT
    af.feedback_type,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
    AVG(af.feedback_confidence) as avg_confidence,
    COUNT(DISTINCT af.alert_id) as unique_alerts
FROM alert_feedback af
GROUP BY af.feedback_type;

-- 视图：告警准确率（基于反馈）
CREATE OR REPLACE VIEW v_alert_accuracy_rate AS
SELECT
    a.alert_type,
    COUNT(*) as total_alerts,
    COALESCE(SUM(CASE WHEN af.feedback_type = 'true_positive' THEN 1 ELSE 0 END), 0) as true_positives,
    COALESCE(SUM(CASE WHEN af.feedback_type = 'false_positive' THEN 1 ELSE 0 END), 0) as false_positives,
    ROUND(
        COALESCE(SUM(CASE WHEN af.feedback_type = 'true_positive' THEN 1 ELSE 0 END), 0) * 100.0 /
        NULLIF(COUNT(*), 0),
        2
    ) as accuracy_percent
FROM alerts a
LEFT JOIN alert_feedback af ON a.alert_id = af.alert_id
GROUP BY a.alert_type;

-- ==================== 7. 辅助函数 ====================

-- 函数：获取指定老人的最近 N 天摘要
CREATE OR REPLACE FUNCTION get_elder_recent_summaries(
    p_elder_id VARCHAR(50),
    p_days INTEGER DEFAULT 7
)
RETURNS TABLE (
    summary_date DATE,
    total_activity_minutes INTEGER,
    sleep_quality_score NUMERIC,
    total_alerts INTEGER,
    critical_alerts INTEGER,
    data_quality_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ds.summary_date,
        ds.total_activity_minutes,
        ds.sleep_quality_score,
        ds.total_alerts,
        ds.critical_alerts,
        ds.data_quality_score
    FROM daily_summaries ds
    WHERE ds.elder_id = p_elder_id
        AND ds.summary_date >= CURRENT_DATE - INTERVAL '1 day' * p_days
    ORDER BY ds.summary_date DESC;
END;
$$ LANGUAGE plpgsql;

-- 函数：计算告警准确率
CREATE OR REPLACE FUNCTION calculate_alert_accuracy_for_family(
    p_family_id VARCHAR(50),
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    alert_type VARCHAR,
    accuracy_percent NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.alert_type,
        ROUND(
            COALESCE(SUM(CASE WHEN af.feedback_type = 'true_positive' THEN 1 ELSE 0 END), 0) * 100.0 /
            NULLIF(COUNT(*), 0),
            2
        ) as accuracy
    FROM alerts a
    LEFT JOIN alert_feedback af ON a.alert_id = af.alert_id
    WHERE a.family_id = p_family_id
        AND a.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day' * p_days
    GROUP BY a.alert_type;
END;
$$ LANGUAGE plpgsql;

-- ==================== 初始化完成 ====================

SELECT
    'maintenance_tables_initialized' as status,
    NOW() as timestamp,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'daily_summaries') as daily_summaries_exists,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'alert_feedback') as alert_feedback_exists;
