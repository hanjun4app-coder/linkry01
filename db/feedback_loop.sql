-- 用户反馈闭环模块
-- 为 alerts 表添加反馈相关字段，支持生成公开访问链接

-- ==================== 1. 修改 alerts 表 ====================

-- 添加反馈相关字段（如果不存在）
ALTER TABLE alerts
ADD COLUMN IF NOT EXISTS feedback_token VARCHAR(64) UNIQUE,
ADD COLUMN IF NOT EXISTS feedback_token_expires_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS feedback_submitted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS feedback_submitted_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS feedback_type VARCHAR(50),  -- true_positive, false_positive
ADD COLUMN IF NOT EXISTS feedback_url VARCHAR(500);

-- 添加索引以加快查询
CREATE INDEX IF NOT EXISTS idx_alert_feedback_token
    ON alerts(feedback_token);

CREATE INDEX IF NOT EXISTS idx_alert_feedback_submitted
    ON alerts(feedback_submitted);

-- ==================== 2. 创建反馈令牌表（用于跟踪） ====================

CREATE TABLE IF NOT EXISTS feedback_tokens (
    id SERIAL PRIMARY KEY,
    token_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    alert_id UUID NOT NULL UNIQUE,
    feedback_token VARCHAR(64) UNIQUE NOT NULL,

    -- 令牌信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT false,
    used_at TIMESTAMP,

    -- 反馈信息
    feedback_type VARCHAR(50),  -- 当令牌被使用时填充
    user_ip VARCHAR(45),        -- 记录用户 IP（可选）
    user_agent TEXT,            -- 记录用户代理（可选）

    CONSTRAINT fk_feedback_token_alert FOREIGN KEY (alert_id) REFERENCES alerts(alert_id),
    CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_feedback_token_alert
    ON feedback_tokens(alert_id);

CREATE INDEX IF NOT EXISTS idx_feedback_token_token
    ON feedback_tokens(feedback_token);

CREATE INDEX IF NOT EXISTS idx_feedback_token_expires
    ON feedback_tokens(expires_at);

-- ==================== 3. 反馈统计视图 ====================

-- 视图：告警反馈统计（不含隐私信息）
CREATE OR REPLACE VIEW v_feedback_loop_stats AS
SELECT
    DATE_TRUNC('day', a.created_at)::DATE as alert_date,
    a.alert_type,
    COUNT(*) as total_alerts,
    SUM(CASE WHEN a.feedback_submitted THEN 1 ELSE 0 END) as feedback_received,
    ROUND(SUM(CASE WHEN a.feedback_submitted THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) as feedback_rate,
    SUM(CASE WHEN a.feedback_type = 'true_positive' THEN 1 ELSE 0 END) as true_positives,
    SUM(CASE WHEN a.feedback_type = 'false_positive' THEN 1 ELSE 0 END) as false_positives
FROM alerts a
GROUP BY DATE_TRUNC('day', a.created_at), a.alert_type
ORDER BY alert_date DESC;

-- 视图：未反馈的告警（用于提醒）
CREATE OR REPLACE VIEW v_alerts_pending_feedback AS
SELECT
    a.alert_id,
    a.elder_id,
    a.family_id,
    a.alert_type,
    a.alert_level,
    a.created_at,
    ft.feedback_token,
    ft.expires_at,
    CASE WHEN ft.expires_at < CURRENT_TIMESTAMP THEN 'expired'
         ELSE 'active' END as token_status,
    EXTRACT(HOUR FROM ft.expires_at - CURRENT_TIMESTAMP) as hours_remaining
FROM alerts a
LEFT JOIN feedback_tokens ft ON a.alert_id = ft.alert_id
WHERE a.feedback_submitted = false
    AND a.created_at > CURRENT_TIMESTAMP - INTERVAL '7 days';

-- ==================== 4. 生成反馈令牌函数 ====================

-- 函数：生成反馈令牌和 URL
CREATE OR REPLACE FUNCTION generate_feedback_token(
    p_alert_id UUID,
    p_token_expiry_hours INTEGER DEFAULT 72  -- 默认 72 小时
)
RETURNS TABLE (
    success BOOLEAN,
    feedback_token VARCHAR(64),
    feedback_url VARCHAR(500),
    expires_at TIMESTAMP,
    message TEXT
) AS $$
DECLARE
    v_token VARCHAR(64);
    v_expires_at TIMESTAMP;
    v_exists BOOLEAN;
BEGIN
    -- 检查令牌是否已存在
    SELECT EXISTS(SELECT 1 FROM alerts WHERE alert_id = p_alert_id AND feedback_token IS NOT NULL)
    INTO v_exists;

    IF v_exists THEN
        -- 令牌已存在，返回现有令牌
        RETURN QUERY
        SELECT
            true,
            a.feedback_token,
            a.feedback_url,
            ft.expires_at,
            'Token already exists'::TEXT
        FROM alerts a
        LEFT JOIN feedback_tokens ft ON a.alert_id = ft.alert_id
        WHERE a.alert_id = p_alert_id;
        RETURN;
    END IF;

    -- 生成新令牌（使用 SHA256 的随机字符串）
    v_token := encode(sha256((random()::text || CURRENT_TIMESTAMP::text)::bytea), 'hex');
    v_expires_at := CURRENT_TIMESTAMP + INTERVAL '1 hour' * p_token_expiry_hours;

    -- 插入令牌记录
    INSERT INTO feedback_tokens (alert_id, feedback_token, expires_at)
    VALUES (p_alert_id, v_token, v_expires_at);

    -- 更新 alerts 表
    UPDATE alerts
    SET
        feedback_token = v_token,
        feedback_token_expires_at = v_expires_at,
        feedback_url = '/feedback/' || p_alert_id::text || '?token=' || v_token
    WHERE alert_id = p_alert_id;

    RETURN QUERY
    SELECT
        true,
        v_token,
        '/feedback/' || p_alert_id::text || '?token=' || v_token,
        v_expires_at,
        'Token generated successfully'::TEXT;

EXCEPTION WHEN OTHERS THEN
    RETURN QUERY
    SELECT
        false,
        NULL::VARCHAR(64),
        NULL::VARCHAR(500),
        NULL::TIMESTAMP,
        'Error: ' || SQLERRM;
END;
$$ LANGUAGE plpgsql;

-- ==================== 5. 验证和提交反馈函数 ====================

-- 函数：验证令牌并提交反馈
CREATE OR REPLACE FUNCTION submit_feedback_with_token(
    p_alert_id UUID,
    p_feedback_token VARCHAR(64),
    p_feedback_type VARCHAR(50),  -- 'true_positive' or 'false_positive'
    p_user_ip VARCHAR(45) DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
)
RETURNS TABLE (
    success BOOLEAN,
    message TEXT
) AS $$
DECLARE
    v_token_valid BOOLEAN;
    v_token_expired BOOLEAN;
    v_already_submitted BOOLEAN;
BEGIN
    -- 检查令牌是否存在且有效
    SELECT EXISTS(
        SELECT 1 FROM feedback_tokens
        WHERE alert_id = p_alert_id
            AND feedback_token = p_feedback_token
            AND is_used = false
            AND expires_at > CURRENT_TIMESTAMP
    ) INTO v_token_valid;

    IF NOT v_token_valid THEN
        -- 检查令牌是否过期
        SELECT EXISTS(
            SELECT 1 FROM feedback_tokens
            WHERE alert_id = p_alert_id
                AND feedback_token = p_feedback_token
                AND expires_at <= CURRENT_TIMESTAMP
        ) INTO v_token_expired;

        IF v_token_expired THEN
            RETURN QUERY SELECT false, 'Token has expired'::TEXT;
        ELSE
            RETURN QUERY SELECT false, 'Invalid token'::TEXT;
        END IF;
        RETURN;
    END IF;

    -- 检查是否已提交过反馈
    SELECT EXISTS(
        SELECT 1 FROM alerts
        WHERE alert_id = p_alert_id
            AND feedback_submitted = true
    ) INTO v_already_submitted;

    IF v_already_submitted THEN
        RETURN QUERY SELECT false, 'Feedback already submitted'::TEXT;
        RETURN;
    END IF;

    -- 验证反馈类型
    IF p_feedback_type NOT IN ('true_positive', 'false_positive') THEN
        RETURN QUERY SELECT false, 'Invalid feedback type'::TEXT;
        RETURN;
    END IF;

    -- 更新 alerts 表
    UPDATE alerts
    SET
        feedback_submitted = true,
        feedback_submitted_at = CURRENT_TIMESTAMP,
        feedback_type = p_feedback_type
    WHERE alert_id = p_alert_id;

    -- 标记令牌已使用
    UPDATE feedback_tokens
    SET
        is_used = true,
        used_at = CURRENT_TIMESTAMP,
        feedback_type = p_feedback_type,
        user_ip = p_user_ip,
        user_agent = p_user_agent
    WHERE alert_id = p_alert_id
        AND feedback_token = p_feedback_token;

    -- 同时更新 alert_feedback 表（如果存在）
    INSERT INTO alert_feedback (
        alert_id, elder_id, family_id,
        feedback_type, feedback_confidence, outcome
    )
    SELECT
        a.alert_id, a.elder_id, a.family_id,
        p_feedback_type, 1.0,
        CASE WHEN p_feedback_type = 'true_positive' THEN 'confirmed'
             ELSE 'dismissed' END
    FROM alerts a
    WHERE a.alert_id = p_alert_id
    ON CONFLICT (alert_id) DO UPDATE SET
        feedback_type = EXCLUDED.feedback_type,
        updated_at = CURRENT_TIMESTAMP;

    RETURN QUERY SELECT true, 'Feedback submitted successfully'::TEXT;

EXCEPTION WHEN OTHERS THEN
    RETURN QUERY SELECT false, 'Error: ' || SQLERRM;
END;
$$ LANGUAGE plpgsql;

-- ==================== 6. 清理过期令牌函数 ====================

-- 函数：清理过期且未使用的令牌
CREATE OR REPLACE FUNCTION cleanup_expired_feedback_tokens()
RETURNS TABLE (
    deleted_count INTEGER,
    message TEXT
) AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    DELETE FROM feedback_tokens
    WHERE expires_at < CURRENT_TIMESTAMP
        AND is_used = false;

    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    RETURN QUERY SELECT v_deleted, 'Deleted ' || v_deleted || ' expired tokens'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- ==================== 7. 定时触发器（可选） ====================

-- 每天清理过期令牌
-- 可以在应用启动时调用或通过 cron 任务定期调用

-- ==================== 初始化完成 ====================

SELECT
    'feedback_loop_initialized' as status,
    NOW() as timestamp,
    (SELECT COUNT(*) FROM alerts) as existing_alerts,
    (SELECT COUNT(*) FROM feedback_tokens) as existing_tokens;
