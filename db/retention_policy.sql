-- 数据保留策略脚本
-- 定义数据过期清理规则

-- ==================== 1. 数据保留配置 ====================

-- 创建保留策略配置表
CREATE TABLE IF NOT EXISTS retention_policies (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL UNIQUE,
    retention_days INTEGER NOT NULL,
    archive_enabled BOOLEAN DEFAULT false,
    last_cleanup_date TIMESTAMP,
    cleanup_interval_hours INTEGER DEFAULT 24,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入保留策略配置
INSERT INTO retention_policies (table_name, retention_days, archive_enabled, enabled)
VALUES
    ('events', 90, true, true),
    ('daily_summaries', 1095, false, true),  -- 3 年
    ('alerts', 1095, true, true),            -- 3 年
    ('alert_feedback', 1095, false, true),   -- 3 年
    ('audit_logs', 365, false, true)         -- 1 年
ON CONFLICT (table_name) DO UPDATE SET
    retention_days = EXCLUDED.retention_days,
    enabled = EXCLUDED.enabled;

-- ==================== 2. 清理存储过程 ====================

-- 过程：清理过期事件
CREATE OR REPLACE FUNCTION cleanup_expired_events(
    p_retention_days INTEGER DEFAULT 90
)
RETURNS TABLE (
    status TEXT,
    rows_deleted INTEGER,
    duration_seconds INTEGER
) AS $$
DECLARE
    v_start_time TIMESTAMP;
    v_deleted_rows INTEGER := 0;
    v_cutoff_date TIMESTAMP;
BEGIN
    v_start_time := CURRENT_TIMESTAMP;
    v_cutoff_date := CURRENT_DATE - INTERVAL '1 day' * p_retention_days;

    -- 删除过期事件
    DELETE FROM events
    WHERE timestamp < v_cutoff_date;

    v_deleted_rows := FOUND;

    -- 记录操作日志
    INSERT INTO data_retention_logs (
        operation_type, table_name, retention_days,
        rows_affected, start_date, end_date, status,
        executed_at, duration_seconds
    ) VALUES (
        'delete', 'events', p_retention_days,
        v_deleted_rows, v_cutoff_date::DATE, CURRENT_DATE, 'completed',
        CURRENT_TIMESTAMP, EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - v_start_time))::INTEGER
    );

    RETURN QUERY
    SELECT
        'success'::TEXT,
        v_deleted_rows,
        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - v_start_time))::INTEGER;
END;
$$ LANGUAGE plpgsql;

-- 过程：清理过期告警反馈
CREATE OR REPLACE FUNCTION cleanup_expired_alert_feedback(
    p_retention_days INTEGER DEFAULT 1095  -- 3 年
)
RETURNS TABLE (
    status TEXT,
    rows_deleted INTEGER,
    duration_seconds INTEGER
) AS $$
DECLARE
    v_start_time TIMESTAMP;
    v_deleted_rows INTEGER := 0;
    v_cutoff_date TIMESTAMP;
BEGIN
    v_start_time := CURRENT_TIMESTAMP;
    v_cutoff_date := CURRENT_DATE - INTERVAL '1 day' * p_retention_days;

    DELETE FROM alert_feedback
    WHERE created_at < v_cutoff_date;

    v_deleted_rows := FOUND;

    INSERT INTO data_retention_logs (
        operation_type, table_name, retention_days,
        rows_affected, start_date, end_date, status,
        executed_at, duration_seconds
    ) VALUES (
        'delete', 'alert_feedback', p_retention_days,
        v_deleted_rows, v_cutoff_date::DATE, CURRENT_DATE, 'completed',
        CURRENT_TIMESTAMP, EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - v_start_time))::INTEGER
    );

    RETURN QUERY
    SELECT
        'success'::TEXT,
        v_deleted_rows,
        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - v_start_time))::INTEGER;
END;
$$ LANGUAGE plpgsql;

-- 过程：清理过期审计日志
CREATE OR REPLACE FUNCTION cleanup_expired_audit_logs(
    p_retention_days INTEGER DEFAULT 365
)
RETURNS TABLE (
    status TEXT,
    rows_deleted INTEGER,
    duration_seconds INTEGER
) AS $$
DECLARE
    v_start_time TIMESTAMP;
    v_deleted_rows INTEGER := 0;
    v_cutoff_date TIMESTAMP;
BEGIN
    v_start_time := CURRENT_TIMESTAMP;
    v_cutoff_date := CURRENT_DATE - INTERVAL '1 day' * p_retention_days;

    DELETE FROM audit_logs
    WHERE created_at < v_cutoff_date;

    v_deleted_rows := FOUND;

    INSERT INTO data_retention_logs (
        operation_type, table_name, retention_days,
        rows_affected, start_date, end_date, status,
        executed_at, duration_seconds
    ) VALUES (
        'delete', 'audit_logs', p_retention_days,
        v_deleted_rows, v_cutoff_date::DATE, CURRENT_DATE, 'completed',
        CURRENT_TIMESTAMP, EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - v_start_time))::INTEGER
    );

    RETURN QUERY
    SELECT
        'success'::TEXT,
        v_deleted_rows,
        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - v_start_time))::INTEGER;
END;
$$ LANGUAGE plpgsql;

-- 过程：执行所有清理任务
CREATE OR REPLACE FUNCTION execute_retention_cleanup()
RETURNS TABLE (
    task_name TEXT,
    status TEXT,
    rows_affected INTEGER
) AS $$
DECLARE
    v_row RECORD;
BEGIN
    -- 清理过期事件
    FOR v_row IN SELECT * FROM cleanup_expired_events(90) LOOP
        RETURN QUERY SELECT 'cleanup_events'::TEXT, v_row.status, v_row.rows_deleted;
    END LOOP;

    -- 清理过期告警反馈
    FOR v_row IN SELECT * FROM cleanup_expired_alert_feedback(1095) LOOP
        RETURN QUERY SELECT 'cleanup_alert_feedback'::TEXT, v_row.status, v_row.rows_deleted;
    END LOOP;

    -- 清理过期审计日志
    FOR v_row IN SELECT * FROM cleanup_expired_audit_logs(365) LOOP
        RETURN QUERY SELECT 'cleanup_audit_logs'::TEXT, v_row.status, v_row.rows_deleted;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ==================== 3. 定时任务支持函数 ====================

-- 函数：生成每日摘要
CREATE OR REPLACE FUNCTION generate_daily_summary(
    p_elder_id VARCHAR(50),
    p_family_id VARCHAR(50),
    p_summary_date DATE DEFAULT CURRENT_DATE - INTERVAL '1 day'
)
RETURNS TABLE (
    success BOOLEAN,
    summary_id UUID,
    message TEXT
) AS $$
DECLARE
    v_summary_id UUID;
    v_total_activity INTEGER;
    v_active_rooms JSONB;
    v_bathroom_visits INTEGER;
    v_avg_bathroom_duration NUMERIC;
    v_total_alerts INTEGER;
    v_critical_alerts INTEGER;
    v_warning_alerts INTEGER;
    v_data_quality_score NUMERIC;
BEGIN
    -- 计算活动指标
    SELECT
        COALESCE(COUNT(*), 0),
        COALESCE(
            jsonb_agg(DISTINCT e.room) FILTER (WHERE e.room IS NOT NULL),
            '[]'::jsonb
        )
    INTO v_total_activity, v_active_rooms
    FROM events e
    WHERE e.elder_id = p_elder_id
        AND DATE(e.timestamp) = p_summary_date;

    -- 计算卫生间指标
    SELECT
        COUNT(*),
        AVG(EXTRACT(EPOCH FROM (e.timestamp)) / 60)
    INTO v_bathroom_visits, v_avg_bathroom_duration
    FROM events e
    WHERE e.elder_id = p_elder_id
        AND e.room = 'bathroom'
        AND DATE(e.timestamp) = p_summary_date;

    -- 计算告警指标
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE alert_level = 'critical'),
        COUNT(*) FILTER (WHERE alert_level = 'warning')
    INTO v_total_alerts, v_critical_alerts, v_warning_alerts
    FROM alerts
    WHERE elder_id = p_elder_id
        AND DATE(created_at) = p_summary_date;

    -- 计算数据质量评分（基于设备在线时间）
    SELECT
        ROUND(
            SUM(CASE WHEN is_online THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0),
            2
        )
    INTO v_data_quality_score
    FROM devices
    WHERE elder_id = p_elder_id
        AND family_id = p_family_id;

    -- 插入或更新摘要
    INSERT INTO daily_summaries (
        elder_id, family_id, summary_date,
        total_activity_minutes, active_rooms,
        bathroom_visits, avg_bathroom_duration_minutes,
        total_alerts, critical_alerts, warning_alerts,
        data_quality_score
    ) VALUES (
        p_elder_id, p_family_id, p_summary_date,
        COALESCE(v_total_activity, 0), v_active_rooms,
        COALESCE(v_bathroom_visits, 0), COALESCE(v_avg_bathroom_duration, 0),
        COALESCE(v_total_alerts, 0), COALESCE(v_critical_alerts, 0), COALESCE(v_warning_alerts, 0),
        COALESCE(v_data_quality_score, 0)
    )
    ON CONFLICT (elder_id, family_id, summary_date) DO UPDATE SET
        total_activity_minutes = EXCLUDED.total_activity_minutes,
        active_rooms = EXCLUDED.active_rooms,
        bathroom_visits = EXCLUDED.bathroom_visits,
        total_alerts = EXCLUDED.total_alerts,
        updated_at = CURRENT_TIMESTAMP
    RETURNING summary_id INTO v_summary_id;

    RETURN QUERY
    SELECT true, v_summary_id, 'Daily summary generated successfully'::TEXT;

EXCEPTION WHEN OTHERS THEN
    RETURN QUERY
    SELECT false, NULL::UUID, SQLERRM;
END;
$$ LANGUAGE plpgsql;

-- ==================== 4. 初始化完成 ====================

SELECT
    'retention_policy_initialized' as status,
    NOW() as timestamp;
