# 后端 API 和数据库设计文档

## 概述

本文档设计了一个完整的后端系统，用于支持家属老人监护的前端应用。

设计目标：
- 与现有前端 `apiClient` 无缝集成
- 支持多家庭、多老人、多设备
- 记录完整的行为事件和反馈数据
- 为数据分析留出扩展空间

---

## 第一部分：数据库 Schema

### 数据库选择：Supabase (Postgres)

优势：
- 无需部署自己的服务器
- 自带认证、RLS、实时数据库
- 免费额度足以小规模使用
- Postgres 生态成熟

---

### 1. homes 表（家庭）

```sql
CREATE TABLE homes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name VARCHAR(255) NOT NULL,                    -- 家庭名称
  address VARCHAR(500),                          -- 地址
  owner_id UUID NOT NULL,                        -- 家庭主人 ID
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- 索引
  UNIQUE(owner_id)                               -- 一个主人一个家庭
);

-- 注释
COMMENT ON TABLE homes IS '家庭信息表';
COMMENT ON COLUMN homes.owner_id IS '家庭主人 ID（通常是成年子女）';
```

**示例数据**：
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "王家（老年公寓）",
  "address": "北京市朝阳区X街X号",
  "owner_id": "uuid-of-owner",
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-04-25T10:00:00Z"
}
```

---

### 2. elders 表（老人）

```sql
CREATE TABLE elders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,                    -- 老人名字
  age INT,                                       -- 年龄
  phone VARCHAR(20),                             -- 电话
  emergency_contact VARCHAR(255),                -- 紧急联系人
  emergency_phone VARCHAR(20),                   -- 紧急电话
  
  -- 健康信息
  health_conditions TEXT,                        -- 健康状况（JSON 格式）
  medications TEXT,                              -- 用药情况（JSON 格式）
  
  -- 时间戳
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- 索引
  FOREIGN KEY (home_id) REFERENCES homes(id),
  INDEX(home_id)
);

COMMENT ON TABLE elders IS '老人信息表';
COMMENT ON COLUMN elders.health_conditions IS '健康状况，JSON 格式存储';
```

**示例数据**：
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "home_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "王奶奶",
  "age": 78,
  "phone": "13800138000",
  "emergency_contact": "王某某（女儿）",
  "emergency_phone": "13900139000",
  "health_conditions": "{\"hypertension\": true, \"diabetes\": false}",
  "medications": "[{\"name\": \"降压药\", \"dosage\": \"1次/天\"}]",
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-04-25T10:00:00Z"
}
```

---

### 3. devices 表（设备）

```sql
CREATE TABLE devices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,                    -- 设备名称（如"卧室传感器"）
  type VARCHAR(50) NOT NULL,                     -- 类型：motion / door / temperature / etc.
  location VARCHAR(100),                         -- 位置（卧室、客厅、卫生间等）
  model VARCHAR(100),                            -- 设备型号
  device_id VARCHAR(100) UNIQUE,                 -- 设备物理 ID（用于识别）
  
  -- 状态
  is_active BOOLEAN DEFAULT true,                -- 是否在线
  last_heartbeat TIMESTAMP,                      -- 最后心跳时间
  
  -- 时间戳
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- 索引
  FOREIGN KEY (home_id) REFERENCES homes(id),
  INDEX(home_id),
  INDEX(type)
);

COMMENT ON TABLE devices IS '智能设备表';
COMMENT ON COLUMN devices.type IS '设备类型：motion（人体传感器）, door（门窗传感器）, temperature（温度计）等';
```

**示例数据**：
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "home_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "卧室人体传感器",
  "type": "motion",
  "location": "bedroom",
  "model": "XYZ-Motion-Sensor-v1",
  "device_id": "DEV-00001",
  "is_active": true,
  "last_heartbeat": "2026-04-25T10:30:00Z",
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-04-25T10:30:00Z"
}
```

---

### 4. behavior_events 表（行为事件）

```sql
CREATE TABLE behavior_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
  elder_id UUID NOT NULL REFERENCES elders(id) ON DELETE CASCADE,
  
  -- 事件类型（与前端 EventType 对应）
  event_type VARCHAR(50) NOT NULL,               -- wake_up, bathroom_long_stay 等
  zone VARCHAR(50),                              -- 位置：bedroom, bathroom 等
  
  -- 事件时间
  start_time TIMESTAMP NOT NULL,                 -- 事件开始时间
  end_time TIMESTAMP,                            -- 事件结束时间（可选）
  duration_minutes INT,                          -- 持续时间（分钟）
  
  -- 风险等级
  risk_level VARCHAR(20) NOT NULL,               -- normal, attention, high
  
  -- 额外信息
  metadata JSONB,                                -- 补充信息，JSON 格式
  
  -- 时间戳
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- 索引
  FOREIGN KEY (home_id) REFERENCES homes(id),
  FOREIGN KEY (elder_id) REFERENCES elders(id),
  INDEX(home_id),
  INDEX(elder_id),
  INDEX(start_time),
  INDEX(event_type),
  INDEX(risk_level)
);

COMMENT ON TABLE behavior_events IS '行为事件表，记录老人的日常活动';
COMMENT ON COLUMN behavior_events.event_type IS '对应前端的 EventType：wake_up, bathroom_use, bathroom_long_stay, no_activity 等';
COMMENT ON COLUMN behavior_events.metadata IS '补充信息，JSON 格式，如设备信息、温度数据等';
```

**示例数据**：
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "home_id": "550e8400-e29b-41d4-a716-446655440000",
  "elder_id": "660e8400-e29b-41d4-a716-446655440001",
  "event_type": "bathroom_long_stay",
  "zone": "bathroom",
  "start_time": "2026-04-25T09:05:00Z",
  "end_time": "2026-04-25T09:30:00Z",
  "duration_minutes": 25,
  "risk_level": "attention",
  "metadata": {
    "triggered_by_device": "DEV-00001",
    "temperature": 22.5,
    "humidity": 65
  },
  "created_at": "2026-04-25T09:30:00Z",
  "updated_at": "2026-04-25T09:30:00Z"
}
```

---

### 5. daily_summaries 表（每日摘要）

```sql
CREATE TABLE daily_summaries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
  elder_id UUID NOT NULL REFERENCES elders(id) ON DELETE CASCADE,
  
  -- 日期
  date DATE NOT NULL,                            -- 摘要日期（YYYY-MM-DD）
  
  -- 统计数据（对应前端 DailyBehaviorSummaryInput）
  wake_time VARCHAR(10),                         -- 起床时间（HH:MM）
  total_active_minutes INT DEFAULT 0,            -- 总活动时间（分钟）
  bathroom_count INT DEFAULT 0,                  -- 卫生间使用次数
  longest_bathroom_minutes INT,                  -- 最长一次卫生间停留（分钟）
  night_wake_count INT DEFAULT 0,                -- 夜间起床次数
  alerts_count INT DEFAULT 0,                    -- 异常提醒数
  highest_risk VARCHAR(20) DEFAULT 'normal',    -- 最高风险等级
  
  -- 额外信息
  notes TEXT,                                    -- 备注
  
  -- 时间戳
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- 索引和唯一性
  FOREIGN KEY (home_id) REFERENCES homes(id),
  FOREIGN KEY (elder_id) REFERENCES elders(id),
  UNIQUE(elder_id, date),                        -- 每个老人每天只有一条摘要
  INDEX(home_id),
  INDEX(elder_id),
  INDEX(date)
);

COMMENT ON TABLE daily_summaries IS '每日摘要表，记录老人每天的活动统计';
```

**示例数据**：
```json
{
  "id": "990e8400-e29b-41d4-a716-446655440004",
  "home_id": "550e8400-e29b-41d4-a716-446655440000",
  "elder_id": "660e8400-e29b-41d4-a716-446655440001",
  "date": "2026-04-25",
  "wake_time": "07:30",
  "total_active_minutes": 180,
  "bathroom_count": 2,
  "longest_bathroom_minutes": 25,
  "night_wake_count": 0,
  "alerts_count": 1,
  "highest_risk": "attention",
  "notes": "今天卫生间停留较长",
  "created_at": "2026-04-25T23:59:00Z",
  "updated_at": "2026-04-25T23:59:00Z"
}
```

---

### 6. risk_alerts 表（风险告警）

```sql
CREATE TABLE risk_alerts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
  elder_id UUID NOT NULL REFERENCES elders(id) ON DELETE CASCADE,
  
  -- 告警信息
  alert_type VARCHAR(50) NOT NULL,               -- bathroom_long_stay, no_activity 等
  risk_level VARCHAR(20) NOT NULL,               -- attention, high
  title VARCHAR(255) NOT NULL,                   -- 告警标题
  description TEXT,                              -- 告警描述
  
  -- 触发事件
  event_id UUID REFERENCES behavior_events(id),
  
  -- 状态
  status VARCHAR(20) DEFAULT 'new',              -- new, acknowledged, resolved
  acknowledged_at TIMESTAMP,                     -- 确认时间
  resolved_at TIMESTAMP,                         -- 解决时间
  
  -- 时间戳
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- 索引
  FOREIGN KEY (home_id) REFERENCES homes(id),
  FOREIGN KEY (elder_id) REFERENCES elders(id),
  INDEX(home_id),
  INDEX(elder_id),
  INDEX(status),
  INDEX(created_at)
);

COMMENT ON TABLE risk_alerts IS '风险告警表，记录需要关注的异常情况';
```

**示例数据**：
```json
{
  "id": "aaa0e8400-e29b-41d4-a716-446655440005",
  "home_id": "550e8400-e29b-41d4-a716-446655440000",
  "elder_id": "660e8400-e29b-41d4-a716-446655440001",
  "alert_type": "bathroom_long_stay",
  "risk_level": "attention",
  "title": "卫生间停留较长",
  "description": "检测到老人在卫生间停留约 25 分钟",
  "event_id": "880e8400-e29b-41d4-a716-446655440003",
  "status": "new",
  "acknowledged_at": null,
  "resolved_at": null,
  "created_at": "2026-04-25T09:30:00Z",
  "updated_at": "2026-04-25T09:30:00Z"
}
```

---

### 7. feedback 表（用户反馈）

```sql
CREATE TABLE feedback (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
  elder_id UUID NOT NULL REFERENCES elders(id) ON DELETE CASCADE,
  
  -- 反馈信息
  alert_id UUID REFERENCES risk_alerts(id),     -- 关联的告警（可选）
  action VARCHAR(50) NOT NULL,                   -- confirmed, need_help, dismiss
  notes TEXT,                                    -- 用户备注
  
  -- 反馈者信息
  submitted_by VARCHAR(255),                     -- 反馈人（家属名字）
  
  -- 时间戳
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- 索引
  FOREIGN KEY (home_id) REFERENCES homes(id),
  FOREIGN KEY (elder_id) REFERENCES elders(id),
  INDEX(home_id),
  INDEX(elder_id),
  INDEX(created_at)
);

COMMENT ON TABLE feedback IS '用户反馈表，记录家属对告警的反应';
COMMENT ON COLUMN feedback.action IS '反馈操作：confirmed（已确认）, need_help（需要帮助）, dismiss（忽略）';
```

**示例数据**：
```json
{
  "id": "bbb0e8400-e29b-41d4-a716-446655440006",
  "home_id": "550e8400-e29b-41d4-a716-446655440000",
  "elder_id": "660e8400-e29b-41d4-a716-446655440001",
  "alert_id": "aaa0e8400-e29b-41d4-a716-446655440005",
  "action": "confirmed",
  "notes": "老人确认无事，进行了正常的卫生活动",
  "submitted_by": "女儿王某某",
  "created_at": "2026-04-25T09:35:00Z",
  "updated_at": "2026-04-25T09:35:00Z"
}
```

---

## 第二部分：API 设计

### API 基础信息

```
BASE_URL: https://api.example.com/api
版本: v1
认证: 简单 API Key（开发阶段）或 Supabase JWT（生产）
响应格式: JSON
```

---

### 1. GET /homes/:homeId/behavior-events

获取行为事件列表。

**请求**：
```http
GET /api/v1/homes/550e8400-e29b-41d4-a716-446655440000/behavior-events?date=2026-04-25&limit=20&offset=0
Authorization: Bearer {token}
```

**查询参数**：
```typescript
{
  date?: string,              // 可选：特定日期（YYYY-MM-DD）
  startDate?: string,         // 可选：开始日期
  endDate?: string,           // 可选：结束日期
  elderIds?: string[],        // 可选：特定老人 ID 列表
  eventTypes?: string[],      // 可选：特定事件类型
  riskLevel?: string,         // 可选：风险等级过滤
  limit?: number,             // 可选：每页数量（默认 20）
  offset?: number,            // 可选：偏移量（默认 0）
  sortBy?: string,            // 可选：排序字段（default: -start_time）
}
```

**响应**（成功 200）：
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "events": [
      {
        "id": "880e8400-e29b-41d4-a716-446655440003",
        "home_id": "550e8400-e29b-41d4-a716-446655440000",
        "elder_id": "660e8400-e29b-41d4-a716-446655440001",
        "event_type": "bathroom_long_stay",
        "zone": "bathroom",
        "start_time": "2026-04-25T09:05:00Z",
        "end_time": "2026-04-25T09:30:00Z",
        "duration_minutes": 25,
        "risk_level": "attention",
        "metadata": {
          "triggered_by_device": "DEV-00001"
        },
        "created_at": "2026-04-25T09:30:00Z"
      },
      {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "event_type": "wake_up",
        "zone": "bedroom",
        "start_time": "2026-04-25T07:30:00Z",
        "risk_level": "normal",
        "created_at": "2026-04-25T07:30:00Z"
      }
    ],
    "pagination": {
      "total": 42,
      "limit": 20,
      "offset": 0,
      "hasMore": true
    }
  }
}
```

**响应**（错误 400/500）：
```json
{
  "code": 400,
  "message": "Invalid home ID",
  "error": {
    "type": "VALIDATION_ERROR",
    "details": "home_id format is invalid"
  }
}
```

---

### 2. GET /homes/:homeId/daily-summary

获取今日摘要。

**请求**：
```http
GET /api/v1/homes/550e8400-e29b-41d4-a716-446655440000/daily-summary?date=2026-04-25
Authorization: Bearer {token}
```

**查询参数**：
```typescript
{
  date?: string,              // 可选：特定日期（YYYY-MM-DD），默认今天
  elderIds?: string[],        // 可选：特定老人 ID 列表，默认所有
}
```

**响应**（成功 200）：
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "summary": {
      "wake_time": "07:30",
      "total_active_minutes": 180,
      "bathroom_count": 2,
      "longest_bathroom_minutes": 25,
      "night_wake_count": 0,
      "alerts_count": 1,
      "highest_risk": "attention"
    },
    "date": "2026-04-25",
    "elderly_summaries": [
      {
        "elder_id": "660e8400-e29b-41d4-a716-446655440001",
        "elder_name": "王奶奶",
        "wake_time": "07:30",
        "total_active_minutes": 180,
        "bathroom_count": 2,
        "longest_bathroom_minutes": 25,
        "night_wake_count": 0,
        "alerts_count": 1,
        "highest_risk": "attention"
      }
    ]
  }
}
```

---

### 3. GET /homes/:homeId/elderly-info

获取老人信息。

**请求**：
```http
GET /api/v1/homes/550e8400-e29b-41d4-a716-446655440000/elderly-info
Authorization: Bearer {token}
```

**响应**（成功 200）：
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "elders": [
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "home_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "王奶奶",
        "age": 78,
        "phone": "13800138000",
        "emergency_contact": "王某某（女儿）",
        "emergency_phone": "13900139000",
        "health_conditions": {
          "hypertension": true,
          "diabetes": false
        },
        "created_at": "2026-01-15T10:00:00Z"
      }
    ],
    "devices": [
      {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "name": "卧室人体传感器",
        "type": "motion",
        "location": "bedroom",
        "is_active": true,
        "last_heartbeat": "2026-04-25T10:30:00Z"
      }
    ]
  }
}
```

---

### 4. POST /homes/:homeId/feedback

提交用户反馈。

**请求**：
```http
POST /api/v1/homes/550e8400-e29b-41d4-a716-446655440000/feedback
Authorization: Bearer {token}
Content-Type: application/json

{
  "elder_id": "660e8400-e29b-41d4-a716-446655440001",
  "alert_id": "aaa0e8400-e29b-41d4-a716-446655440005",
  "action": "confirmed",
  "notes": "老人确认无事",
  "submitted_by": "女儿王某某"
}
```

**请求体**：
```typescript
{
  elder_id: string,           // 必需：老人 ID
  alert_id?: string,          // 可选：关联的告警 ID
  action: string,             // 必需：confirmed | need_help | dismiss
  notes?: string,             // 可选：备注
  submitted_by?: string,      // 可选：反馈人名字
}
```

**响应**（成功 200）：
```json
{
  "code": 200,
  "message": "Feedback submitted successfully",
  "data": {
    "feedback_id": "bbb0e8400-e29b-41d4-a716-446655440006",
    "action": "confirmed",
    "alert_id": "aaa0e8400-e29b-41d4-a716-446655440005",
    "created_at": "2026-04-25T09:35:00Z",
    "alert_status": "acknowledged"
  }
}
```

---

## 第三部分：后端技术建议

### 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **Supabase + Next.js** | 全栈整合，快速开发，自动扩展 | 无冷启动控制 | ⭐⭐⭐⭐⭐ |
| **Supabase + FastAPI** | 高性能，异步优先，成熟生态 | 需要额外部署 | ⭐⭐⭐⭐ |
| **自建 Express** | 灵活，学习资源多 | 需要自己维护，认证复杂 | ⭐⭐⭐ |
| **Firebase** | 完全无服务器，实时数据库 | 成本不可控，厂商锁定 | ⭐⭐⭐ |

### 推荐方案：Supabase + Next.js API Routes

**原因**：
1. Supabase 提供开箱即用的 Postgres + 认证
2. Next.js 可以在同一个仓库中管理前后端
3. API Routes 在 `/api` 目录中，易于组织
4. 可以直接在路由中使用 Supabase SDK
5. 部署简单（Vercel）

---

### 文件结构（推荐）

```
elderly-care/
├── app/
│   ├── (web)/
│   │   ├── page.tsx          # 首页
│   │   └── dashboard/
│   │       └── page.tsx      # 监护面板
│   │
│   └── api/
│       └── v1/
│           ├── homes/
│           │   ├── [homeId]/
│           │   │   ├── behavior-events/
│           │   │   │   └── route.ts         # GET
│           │   │   ├── daily-summary/
│           │   │   │   └── route.ts         # GET
│           │   │   ├── elderly-info/
│           │   │   │   └── route.ts         # GET
│           │   │   └── feedback/
│           │   │       └── route.ts         # POST
│           │   └── route.ts
│           │
│           └── health/
│               └── route.ts                 # 健康检查
│
├── lib/
│   ├── supabase.ts                          # Supabase 客户端
│   ├── apiClient.ts                         # API 客户端（保持不变）
│   └── auth.ts                              # 认证工具
│
├── types/
│   └── api.ts                               # API 类型（保持不变）
│
└── package.json
```

---

### 实现关键点

#### 1. Supabase 初始化

```typescript
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseKey);

export const supabaseAdmin = createClient(
  supabaseUrl,
  process.env.SUPABASE_SERVICE_ROLE_KEY! // 服务器端只用
);
```

#### 2. 环境变量

```env
# .env.local
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyxxx...
SUPABASE_SERVICE_ROLE_KEY=eyxxx...
```

#### 3. API Route 示例

```typescript
// app/api/v1/homes/[homeId]/behavior-events/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET(
  request: NextRequest,
  { params }: { params: { homeId: string } }
) {
  try {
    const { homeId } = params;
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '20');
    const offset = parseInt(searchParams.get('offset') || '0');

    // 查询数据库
    const { data, error, count } = await supabase
      .from('behavior_events')
      .select('*', { count: 'exact' })
      .eq('home_id', homeId)
      .order('start_time', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) throw error;

    return NextResponse.json({
      code: 200,
      message: 'Success',
      data: {
        events: data,
        pagination: {
          total: count || 0,
          limit,
          offset,
          hasMore: (count || 0) > offset + limit,
        },
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        code: 500,
        message: 'Internal server error',
      },
      { status: 500 }
    );
  }
}
```

---

## 第四部分：认证和安全建议

### 开发阶段（现在）

使用简单的 API Key：

```typescript
// lib/auth.ts
export function validateApiKey(key: string): boolean {
  return key === process.env.NEXT_PUBLIC_API_KEY;
}
```

### 生产阶段（未来）

迁移到 Supabase Auth + RLS：

```sql
-- 行级安全 (RLS)
ALTER TABLE behavior_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their home's events"
  ON behavior_events
  FOR SELECT
  USING (
    home_id IN (
      SELECT id FROM homes WHERE owner_id = auth.uid()
    )
  );
```

---

## 第五部分：部署建议

### Supabase 部署

1. 创建 Supabase 项目：https://supabase.com
2. 导入 schema（SQL）
3. 获取 URL 和 Key
4. 添加到环境变量

### Next.js 部署

1. 推送到 GitHub
2. 连接 Vercel
3. 自动部署
4. 配置环境变量

---

## 总结

这个设计让你可以：

✅ **前端无缝切换** - 只需改 apiClient 的 baseUrl 和 enableMockData  
✅ **数据结构清晰** - 表设计完整，索引优化  
✅ **API 设计标准** - RESTful，符合行业规范  
✅ **安全可扩展** - 支持认证和权限控制  
✅ **快速实现** - Supabase 省去后端基础建设  

---

**下一步**：按照这个设计实现 Supabase + Next.js 后端！
