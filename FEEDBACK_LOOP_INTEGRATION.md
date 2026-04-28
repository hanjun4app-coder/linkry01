# 用户反馈闭环集成指南

## 概述

本文档说明如何将用户反馈闭环功能集成到现有系统中。

**新增功能**：
- 公开反馈 API 端点（无需 API key）
- 反馈令牌生成与验证
- 简单 HTML 反馈表单
- 告警反馈提交

**文件清单**：
- `db/feedback_loop.sql` - 数据库 schema 修改
- `app/routes/public.py` - 公开 API 路由
- `app/services_feedback.py` - 反馈令牌服务
- 本文件 - 集成指南

---

## 第一步：执行数据库脚本

执行 SQL 脚本以创建必要的表、函数和视图：

```bash
psql -U elderly_admin -d elderly_care -f db/feedback_loop.sql
```

验证执行成功：

```bash
psql -U elderly_admin -d elderly_care -c "
  SELECT table_name FROM information_schema.tables 
  WHERE table_schema = 'public' AND table_name = 'feedback_tokens';"
```

应该看到 `feedback_tokens` 表被创建。

---

## 第二步：更新 app/main.py

在现有 main.py 中添加公开路由的注册。

### 添加导入

在 imports 部分添加：

```python
from app.routes import public
```

### 注册路由

在应用初始化后添加（通常在其他路由注册之后）：

```python
# 注册公开路由（反馈闭环）
app.include_router(public.router)
```

### 示例（完整的 main.py 部分）

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routes import events, alerts, patterns, maintenance, public  # 添加 public
from app.tasks import scheduled_tasks
# ... 其他导入

app = FastAPI(
    title="Elderly Care AI",
    description="AI-powered elderly care system",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(events.router)
app.include_router(alerts.router)
app.include_router(patterns.router)
app.include_router(maintenance.router)
app.include_router(public.router)  # 添加这一行

# 启动/关闭事件
@app.on_event("startup")
async def startup():
    await scheduled_tasks.start()

@app.on_event("shutdown")
async def shutdown():
    await scheduled_tasks.stop()
```

---

## 第三步：更新 app/routes/alerts.py

在告警创建时自动生成反馈令牌。

### 修改告警创建端点

在 `POST /api/alerts` 或 `POST /api/events` 处理函数中，在创建告警后调用令牌生成：

```python
from app.services_feedback import FeedbackTokenService

# 在告警创建后添加
@router.post("/api/alerts")
async def create_alert(alert_data: AlertCreate, db: Session = Depends(get_db)):
    """创建告警端点"""
    
    # ... 现有的告警创建逻辑 ...
    
    # 创建告警对象
    alert = Alert(
        alert_id=...,
        alert_type=...,
        # ... 其他字段
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    # 生成反馈令牌
    success, token, feedback_url = FeedbackTokenService.generate_feedback_token(
        db=db,
        alert_id=str(alert.alert_id),
        token_expiry_hours=72  # 72 小时后过期
    )
    
    if success:
        logger.info(f"反馈令牌已生成: {feedback_url}")
        # 可选：将 feedback_url 包含在响应中
        # 或发送短信时包含此 URL
    
    return {
        "alert_id": str(alert.alert_id),
        "feedback_url": feedback_url if success else None,
        # ... 其他响应字段
    }
```

### 在短信通知中包含反馈链接

如果系统发送短信通知，更新短信内容以包含反馈 URL：

```python
async def send_alert_sms(alert_id: str, phone: str, db: Session):
    """发送告警短信"""
    
    # 获取反馈 URL
    feedback_url = FeedbackTokenService.get_feedback_url(db, alert_id)
    
    # 构建短信内容
    sms_content = f"""
    [告警通知]
    您的家人有异常检测。
    
    请点击反馈链接确认告警准确性：
    {feedback_url}
    
    链接 72 小时内有效。
    """
    
    # 发送短信
    send_sms(phone, sms_content)
```

---

## 第四步：验证集成

### 验证 1：检查数据库对象

```bash
# 检查 feedback_tokens 表
psql -U elderly_admin -d elderly_care -c "
  SELECT * FROM feedback_tokens LIMIT 1;"

# 检查函数
psql -U elderly_admin -d elderly_care -c "
  SELECT proname FROM pg_proc WHERE proname LIKE 'generate_feedback%';"
```

### 验证 2：测试 API 端点

```bash
# 1. 创建一个告警（获取 alert_id）
curl -X POST http://localhost:8000/api/alerts \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "elder_id": "elder_001",
    "family_id": "family_001",
    "alert_type": "fall_detection",
    "alert_level": "critical"
  }'

# 从响应中获取 alert_id 和 feedback_url
# 例如：
# {
#   "alert_id": "123e4567-e89b-12d3-a456-426614174000",
#   "feedback_url": "/public/alerts/123e4567-e89b-12d3-a456-426614174000?token=abc123..."
# }

# 2. 访问反馈表单页面
curl "http://localhost:8000/public/alerts/YOUR_ALERT_ID?token=YOUR_TOKEN"

# 应该返回 HTML 页面

# 3. 提交反馈
curl -X POST "http://localhost:8000/public/alerts/YOUR_ALERT_ID/feedback?token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_type": "true_positive"
  }'

# 应该返回：
# {
#   "success": true,
#   "message": "反馈已成功提交，感谢您的反馈！"
# }
```

### 验证 3：检查数据库记录

```bash
# 检查反馈令牌
psql -U elderly_admin -d elderly_care -c "
  SELECT alert_id, feedback_token, is_used, expires_at 
  FROM feedback_tokens 
  ORDER BY created_at DESC LIMIT 5;"

# 检查反馈提交记录
psql -U elderly_admin -d elderly_care -c "
  SELECT alert_id, feedback_type, feedback_submitted, feedback_submitted_at 
  FROM alerts 
  WHERE feedback_submitted = true 
  ORDER BY feedback_submitted_at DESC 
  LIMIT 5;"
```

---

## API 端点说明

### GET /public/alerts/{alert_id}

获取反馈表单页面

**参数**：
- `alert_id` (path): 告警 ID
- `token` (query): 反馈令牌

**响应**：
- 200: HTML 反馈表单页面
- 400: 令牌无效或过期

**示例**：
```bash
curl "http://localhost:8000/public/alerts/ALERT_ID?token=TOKEN"
```

### POST /public/alerts/{alert_id}/feedback

提交反馈

**参数**：
- `alert_id` (path): 告警 ID
- `token` (query): 反馈令牌
- `feedback_type` (body): 反馈类型（'true_positive' 或 'false_positive'）

**请求体**：
```json
{
  "feedback_type": "true_positive"
}
```

**响应**：
```json
{
  "success": true,
  "message": "反馈已成功提交，感谢您的反馈！"
}
```

**错误码**：
- 400: 令牌无效、过期或反馈类型无效
- 409: 反馈已提交
- 500: 系统错误

---

## 令牌管理

### 令牌生成

默认使用 72 小时过期时间。可在调用时修改：

```python
success, token, feedback_url = FeedbackTokenService.generate_feedback_token(
    db=db,
    alert_id=alert_id,
    token_expiry_hours=24  # 修改为 24 小时
)
```

### 令牌清理

过期的未使用令牌应定期清理。可在定时任务中调用：

```python
from app.services_feedback import FeedbackTokenService

async def cleanup_expired_tokens(db: Session):
    """清理过期令牌"""
    success, deleted_count = FeedbackTokenService.cleanup_expired_tokens(db)
    if success:
        logger.info(f"清理了 {deleted_count} 个过期令牌")
```

---

## 短信集成示例

如果系统使用 SMS 服务（如 Twilio），更新短信服务以包含反馈链接：

```python
from app.services_feedback import FeedbackTokenService

async def send_alert_notification(alert_id: str, phone: str, db: Session):
    """发送告警通知（包含反馈链接）"""
    
    # 获取反馈 URL
    feedback_url = FeedbackTokenService.get_feedback_url(db, alert_id)
    
    # 构建短信
    if feedback_url:
        message = f"""
        🚨 告警通知
        
        检测到异常情况。
        请点击链接反馈：
        {feedback_url}
        
        链接 72 小时内有效。
        """
    else:
        message = "检测到异常情况，请联系管理员。"
    
    # 使用 SMS 提供商（Twilio、阿里云、腾讯云等）发送
    await sms_provider.send(phone, message)
```

---

## 数据查询

### 查询特定告警的反馈信息

```sql
SELECT
    a.alert_id,
    a.alert_type,
    a.feedback_submitted,
    a.feedback_type,
    a.feedback_submitted_at,
    ft.expires_at,
    ft.is_used
FROM alerts a
LEFT JOIN feedback_tokens ft ON a.alert_id = ft.alert_id
WHERE a.alert_id = '123e4567-e89b-12d3-a456-426614174000';
```

### 查询反馈统计

```sql
SELECT
    DATE_TRUNC('day', a.created_at)::DATE as alert_date,
    a.alert_type,
    COUNT(*) as total_alerts,
    SUM(CASE WHEN a.feedback_submitted THEN 1 ELSE 0 END) as feedback_received,
    SUM(CASE WHEN a.feedback_type = 'true_positive' THEN 1 ELSE 0 END) as true_positives,
    SUM(CASE WHEN a.feedback_type = 'false_positive' THEN 1 ELSE 0 END) as false_positives
FROM alerts a
GROUP BY DATE_TRUNC('day', a.created_at), a.alert_type
ORDER BY alert_date DESC;
```

### 查询待反馈的告警

```sql
SELECT
    a.alert_id,
    a.alert_type,
    a.alert_level,
    a.created_at,
    ft.expires_at,
    EXTRACT(HOUR FROM ft.expires_at - CURRENT_TIMESTAMP) as hours_remaining
FROM alerts a
LEFT JOIN feedback_tokens ft ON a.alert_id = ft.alert_id
WHERE a.feedback_submitted = false
    AND a.created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY a.created_at DESC;
```

---

## 故障排除

### 问：令牌生成失败

**解决方案**：
1. 检查数据库连接
2. 检查 PostgreSQL 是否已执行 `feedback_loop.sql`
3. 查看应用日志了解详细错误信息

### 问：反馈 URL 格式不对

**解决方案**：
1. 检查 API 基础 URL 配置（如是否需要 `/api` 前缀）
2. 根据需要调整 URL 格式
3. 确保 `/public` 路由已正确注册

### 问：无法访问反馈页面

**解决方案**：
1. 检查 token 是否正确
2. 检查令牌是否已过期
3. 检查应用日志中的错误

### 问：反馈提交返回 400 错误

**解决方案**：
1. 检查 `feedback_type` 是否为 'true_positive' 或 'false_positive'
2. 检查令牌是否有效且未过期
3. 检查是否已提交过反馈

---

## 安全考虑

1. **令牌安全**：
   - 令牌使用 SHA256 加密生成
   - 每个告警只能生成一个有效令牌
   - 令牌具有有效期限制

2. **访问控制**：
   - 反馈 API 不需要 API key（允许公开访问）
   - 令牌本身作为访问凭证

3. **数据审计**：
   - 记录 IP 地址和 User-Agent
   - 防止重复提交

4. **建议**：
   - 定期清理过期令牌
   - 监控异常反馈模式
   - 在生产环境中启用 HTTPS

---

## 性能优化

1. **索引**：
   - `feedback_tokens` 表已有必要索引
   - 定期检查查询性能

2. **令牌清理**：
   - 在定时任务中定期清理过期令牌
   - 推荐每周执行一次

3. **缓存**：
   - 可选：缓存反馈统计数据
   - 可选：缓存常用查询

---

## 下一步

1. ✅ 执行数据库脚本
2. ✅ 更新 main.py 注册路由
3. ✅ 更新 alerts.py 集成令牌生成
4. ✅ 测试 API 端点
5. ✅ 集成短信通知
6. ⏭️ 监控和优化

---

**集成完成后，系统将支持**：

✅ 自动为每个告警生成唯一的反馈链接
✅ 用户可通过短信中的链接提交反馈
✅ 简单直观的反馈表单界面
✅ 完整的反馈数据审计记录
✅ 反馈统计和准确率分析
