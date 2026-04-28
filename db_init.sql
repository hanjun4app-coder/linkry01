-- PostgreSQL 初始化脚本
-- 创建扩展和初始数据

-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建时区时间戳类型（便于时区转换）
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ==================== 初始化用户数据 ====================

-- 示例1: 创建测试家庭
INSERT INTO families (family_id, name, description, created_at, updated_at)
VALUES (
    'family_001',
    '李家',
    '北京朝阳区,2人家庭',
    NOW(),
    NOW()
) ON CONFLICT (family_id) DO NOTHING;

INSERT INTO families (family_id, name, description, created_at, updated_at)
VALUES (
    'family_002',
    '王家',
    '上海浦东,3人家庭',
    NOW(),
    NOW()
) ON CONFLICT (family_id) DO NOTHING;

-- 示例2: 创建测试老人
INSERT INTO elders (elder_id, family_id, name, age, gender, baseline_status, baseline_days_collected, created_at, updated_at)
VALUES (
    'elder_001',
    'family_001',
    '李奶奶',
    78,
    'F',
    'collecting',
    0,
    NOW(),
    NOW()
) ON CONFLICT (elder_id) DO NOTHING;

INSERT INTO elders (elder_id, family_id, name, age, gender, baseline_status, baseline_days_collected, created_at, updated_at)
VALUES (
    'elder_002',
    'family_001',
    '李爷爷',
    82,
    'M',
    'collecting',
    0,
    NOW(),
    NOW()
) ON CONFLICT (elder_id) DO NOTHING;

INSERT INTO elders (elder_id, family_id, name, age, gender, baseline_status, baseline_days_collected, created_at, updated_at)
VALUES (
    'elder_003',
    'family_002',
    '王妈妈',
    75,
    'F',
    'collecting',
    0,
    NOW(),
    NOW()
) ON CONFLICT (elder_id) DO NOTHING;

-- 示例3: 创建测试设备
INSERT INTO devices (device_id, device_type, family_id, elder_id, room, name, description, is_online, created_at, updated_at)
VALUES (
    'aqara_fp2_bedroom',
    'aqara_fp2',
    'family_001',
    'elder_001',
    'bedroom',
    'Aqara FP2 卧室传感器',
    '卧室人体传感器',
    true,
    NOW(),
    NOW()
) ON CONFLICT (device_id) DO NOTHING;

INSERT INTO devices (device_id, device_type, family_id, elder_id, room, name, description, is_online, created_at, updated_at)
VALUES (
    'aqara_fp2_living_room',
    'aqara_fp2',
    'family_001',
    'elder_001',
    'living_room',
    'Aqara FP2 客厅传感器',
    '客厅人体传感器',
    true,
    NOW(),
    NOW()
) ON CONFLICT (device_id) DO NOTHING;

INSERT INTO devices (device_id, device_type, family_id, elder_id, room, name, description, is_online, created_at, updated_at)
VALUES (
    'bathroom_door_sensor',
    'door_sensor',
    'family_001',
    'elder_001',
    'bathroom',
    '卫生间门磁',
    '卫生间门开关传感器',
    true,
    NOW(),
    NOW()
) ON CONFLICT (device_id) DO NOTHING;

INSERT INTO devices (device_id, device_type, family_id, elder_id, room, name, description, is_online, created_at, updated_at)
VALUES (
    'bedroom_temp_humidity',
    'temp_humidity',
    'family_001',
    'elder_001',
    'bedroom',
    '卧室温湿度传感器',
    '温度湿度监测',
    true,
    NOW(),
    NOW()
) ON CONFLICT (device_id) DO NOTHING;

-- ==================== 创建初始模式（基线） ====================

-- 示例: 创建活动模式
INSERT INTO patterns (
    elder_id, family_id, pattern_type,
    average_daily_activity_minutes, average_wake_time, average_sleep_time,
    average_bathroom_count, average_bathroom_duration_minutes,
    usual_active_rooms, confidence, status, days_collected,
    baseline_date, created_at, updated_at
) VALUES (
    'elder_001', 'family_001', 'activity',
    180, '07:00', '22:00',
    4, 15,
    '["living_room", "kitchen", "bedroom"]'::jsonb, 0.8, 'collecting', 0,
    NOW(), NOW(), NOW()
) ON CONFLICT DO NOTHING;

-- ==================== 用户和权限（可选） ====================

-- 如果需要用户认证，可以在这里添加用户表

-- ==================== 创建视图（可选） ====================

-- 视图: 最近的告警
CREATE OR REPLACE VIEW v_recent_alerts AS
SELECT
    a.id, a.alert_id, a.alert_type, a.alert_level, a.message,
    a.elder_id, a.family_id, a.is_acknowledged,
    a.created_at, e.name as elder_name
FROM alerts a
LEFT JOIN elders e ON a.elder_id = e.elder_id
ORDER BY a.created_at DESC
LIMIT 100;

-- 视图: 活跃设备统计
CREATE OR REPLACE VIEW v_device_stats AS
SELECT
    d.family_id,
    d.device_type,
    COUNT(DISTINCT d.device_id) as device_count,
    SUM(CASE WHEN d.is_online = true THEN 1 ELSE 0 END) as online_count,
    MAX(d.last_seen) as last_activity
FROM devices d
GROUP BY d.family_id, d.device_type;

-- 视图: 老人活动摘要
CREATE OR REPLACE VIEW v_elder_activity_summary AS
SELECT
    e.elder_id,
    e.name,
    e.family_id,
    COUNT(DISTINCT ev.id) as total_events_today,
    COUNT(DISTINCT ev.room) as active_rooms,
    MAX(ev.timestamp) as last_activity_time,
    MIN(ev.timestamp) as first_activity_time
FROM elders e
LEFT JOIN events ev ON e.elder_id = ev.elder_id
    AND DATE(ev.timestamp) = CURRENT_DATE
GROUP BY e.elder_id, e.name, e.family_id;

-- ==================== 创建索引（性能优化） ====================

-- 事件表索引（已在模型中定义，但可以手动确认）
CREATE INDEX IF NOT EXISTS idx_event_elder_timestamp
    ON events(elder_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_event_family_timestamp
    ON events(family_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_event_room
    ON events(room);

-- 告警表索引
CREATE INDEX IF NOT EXISTS idx_alert_elder_timestamp
    ON alerts(elder_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_alert_family_timestamp
    ON alerts(family_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_alert_acknowledged
    ON alerts(is_acknowledged);

-- 模式表索引
CREATE INDEX IF NOT EXISTS idx_pattern_elder_type
    ON patterns(elder_id, pattern_type);

-- ==================== 创建函数（可选） ====================

-- 函数: 自动更新 updated_at 时间戳
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有表创建触发器
CREATE TRIGGER update_families_timestamp BEFORE UPDATE ON families
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_elders_timestamp BEFORE UPDATE ON elders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_devices_timestamp BEFORE UPDATE ON devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_patterns_timestamp BEFORE UPDATE ON patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alerts_timestamp BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==================== 初始化完成 ====================

-- 显示初始化结果
SELECT
    (SELECT COUNT(*) FROM families) as family_count,
    (SELECT COUNT(*) FROM elders) as elder_count,
    (SELECT COUNT(*) FROM devices) as device_count,
    (SELECT COUNT(*) FROM patterns) as pattern_count,
    NOW() as initialized_at;
