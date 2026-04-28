# ⚡ 快速部署指南 (5分钟)

**目标**: 从零到生产，最快速的部署路径

---

## 🚀 部署方式选择

选择你的部署方式：

### 方式A：**自动化部署**（推荐）⭐⭐⭐

```bash
# 1. 赋予脚本执行权限
chmod +x QUICK_DEPLOY.sh

# 2. 运行自动化部署脚本
./QUICK_DEPLOY.sh

# 等待脚本完成（约3-5分钟）
# 脚本会自动：
# ✅ 检查环境
# ✅ 备份数据库
# ✅ 安装依赖
# ✅ 运行迁移
# ✅ 验证代码
# ✅ 构建项目
# ✅ 测试API
# ✅ 生成报告
```

**优点**: 全自动，零失误，生成报告  
**缺点**: 无法自定义细节

---

### 方式B：**手动部署**（快速版）

如果自动化脚本失败或你想手动控制，按这个顺序做：

#### **Step 1: 环境检查** (1分钟)

```bash
# 检查必需工具
node --version      # 应该 ≥ 16.x
npm --version       # 应该 ≥ 8.x
psql --version      # PostgreSQL 12+

# 检查项目
ls package.json
ls src/lib/statusEngineV2.ts
ls src/components/EnhancedStatusView.tsx
```

#### **Step 2: 备份数据库** (2分钟)

```bash
# 创建备份（生产环境必须）
pg_dump -U postgres your_db_name > backup_$(date +%Y%m%d_%H%M%S).sql

# 验证备份
ls -lh backup_*.sql
```

#### **Step 3: 运行迁移** (1分钟)

```bash
# 执行数据库迁移
npm run migrate:up

# 或手动执行（如果没有migrate命令）
psql -U postgres your_db_name << EOF
ALTER TABLE elders 
ADD COLUMN IF NOT EXISTS baseline JSONB DEFAULT NULL,
ADD COLUMN IF NOT EXISTS temporary_condition JSONB DEFAULT NULL;

UPDATE elders 
SET baseline = jsonb_build_object(
  'elder_id', elder_id,
  'baseline_status', 'collecting',
  'baseline_days_collected', 0,
  'average_daily_activity_minutes', 180,
  'average_bathroom_count', 4,
  'average_bathroom_duration_minutes', 15,
  'average_night_wake_count', 1,
  'average_daytime_bed_minutes', 60,
  'average_wake_time', 7,
  'average_sleep_time', 22,
  'usual_active_zones', '["living_room", "kitchen", "bathroom"]',
  'created_at', NOW()::text,
  'last_updated_at', NOW()::text,
  'days_in_temporary_condition', 0
)
WHERE baseline IS NULL;
EOF

# 验证迁移
psql -U postgres your_db_name -c "SELECT COUNT(*) as elders_with_baseline FROM elders WHERE baseline IS NOT NULL;"
```

#### **Step 4: 安装依赖** (1分钟)

```bash
# 安装项目依赖
npm install

# 验证安装
npm list next react
```

#### **Step 5: 构建项目** (2分钟)

```bash
# 构建生产版本
npm run build

# 验证构建成功
ls -la .next/
```

#### **Step 6: 启动服务** (1分钟)

```bash
# 开发环境测试
npm run dev &

# 等待启动
sleep 5

# 验证API
curl http://localhost:3000/api/elders/elder_1/status

# 检查响应是否包含: status, baseline, personalizedSignals, temporaryCondition
```

#### **Step 7: 生产启动** (1分钟)

```bash
# 停止开发服务
pkill -f "next dev"

# 启动生产服务
npm run start &

# 验证服务运行
sleep 5
curl http://localhost:3000/api/elders/elder_1/status
```

---

## ✅ 验证清单

部署完成后，检查这些项：

```bash
# 1. 数据库已迁移
psql -U postgres your_db_name -c "SELECT column_name FROM information_schema.columns WHERE table_name='elders' AND column_name IN ('baseline', 'temporary_condition');"
# 应该显示 2 行

# 2. elder已初始化
psql -U postgres your_db_name -c "SELECT COUNT(*) as count FROM elders WHERE baseline IS NOT NULL;"
# 应该显示 > 0

# 3. API正常
curl -s http://localhost:3000/api/elders/elder_1/status | jq . | head -20
# 应该包含 status, baseline, personalizedSignals, temporaryCondition

# 4. 页面可访问
curl -s http://localhost:3000/elders/elder_1 | grep -i "enhanced"
# 应该找到组件名称
```

---

## 🎯 部署后的第一步

### 1. 检查日志

```bash
# 查看应用日志
tail -f logs/application.log

# 查看数据库日志（如果启用）
tail -f logs/database.log
```

### 2. 测试API

```bash
# 获取所有elder的状态
curl http://localhost:3000/api/elders/elder_1/status

# 应该返回 (示例)
{
  "status": {
    "elder_id": "elder_1",
    "risk_level": "normal",
    "alert_message": "✅ 一切正常，今天没有异常检测。",
    "activity_minutes": 180,
    "alert_count": 0,
    "timestamp": "2024-04-26T12:00:00.000Z"
  },
  "baseline": {
    "elder_id": "elder_1",
    "baseline_status": "collecting",
    "baseline_days_collected": 0,
    "average_daily_activity_minutes": 180,
    ...
  },
  "personalizedSignals": [],
  "temporaryCondition": null
}
```

### 3. 访问前端

```bash
# 打开浏览器
open http://localhost:3000/elders/elder_1

# 或
curl http://localhost:3000/elders/elder_1
```

---

## ⚠️ 如果部署失败

### 问题: 迁移失败
```bash
# 检查当前baseline列是否存在
psql -d your_db -c "\d elders" | grep baseline

# 如果存在，跳过迁移
# 如果不存在，运行上面的SQL语句
```

### 问题: API返回500
```bash
# 检查日志找到错误
tail -f logs/error.log

# 检查数据库连接
psql -d your_db -c "SELECT 1"

# 检查baseline数据是否为NULL
psql -d your_db -c "SELECT elder_id, baseline IS NULL FROM elders LIMIT 5"
```

### 问题: 依赖安装失败
```bash
# 清理npm缓存
npm cache clean --force

# 重新安装
rm -rf node_modules package-lock.json
npm install
```

---

## 🚀 下一步（部署成功后）

### 立即做：
```
✅ 验证系统运行正常 (上面的检查清单)
✅ 查看基础API响应
✅ 检查数据库数据
```

### 第1周：
```
📈 配置监控和告警
📊 收集性能基线数据
🔍 执行第1阶段优化（见OPTIMIZATION_ROADMAP.md）
```

### 第2-3周：
```
🎨 执行UI功能优化
⚡ 实现实时更新
📢 进行用户反馈收集
```

---

## 📊 部署成功的标志

✅ 如果看到这些，说明部署成功：

```
✅ npm run build 完成无错误
✅ npm run start 启动无错误
✅ 数据库迁移完成
✅ 所有elder的baseline已初始化
✅ API /api/elders/[id]/status 返回200
✅ 响应包含 status, baseline, personalizedSignals, temporaryCondition
✅ 浏览器可访问 /elders/[id] 页面
✅ EnhancedStatusView 组件正常渲染
```

---

## 📋 快速参考

### 常用命令

```bash
# 开发
npm run dev          # 启动开发服务器

# 生产
npm run build        # 构建
npm run start        # 启动生产服务器

# 数据库
npm run migrate:up   # 运行迁移
npm run migrate:down # 回滚迁移

# 测试
npm test             # 运行测试
npm run lint         # 代码质量检查

# 监控
tail -f logs/app.log          # 应用日志
curl http://localhost:3000/api/elders/elder_1/status  # 测试API
```

### 环境变量

```bash
# .env.local
DATABASE_URL=postgres://user:pass@localhost/db_name
NODE_ENV=production
PORT=3000
LOG_LEVEL=info
```

### 对外端口

```
API:     http://localhost:3000/api/elders/[id]/status
Web:     http://localhost:3000/elders/[id]
Admin:   http://localhost:3000/admin/metrics/baseline
```

---

## 🎓 学到这里你已经知道

✅ 系统架构如何工作  
✅ 数据库如何存储baseline  
✅ API如何返回增强数据  
✅ UI如何显示个性化信号  
✅ 如何部署到生产环境  
✅ 如何验证部署成功  
✅ 如何排查常见问题  
✅ 后续优化方向  

---

## 🎉 部署完成！

恭喜！你现在有一个完全功能的**基线学习系统**在运行。

**接下来**：
1. 收集初期用户反馈
2. 监视系统性能
3. 参考 OPTIMIZATION_ROADMAP.md 计划优化

**问题**：查看 IMPLEMENTATION_STEP_BY_STEP.md 或 DEPLOYMENT_CHECKLIST.md

---

**祝一切顺利！** 🚀

最后更新: April 26, 2026 | 预计部署时间: 5分钟
