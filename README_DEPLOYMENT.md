# 基线学习集成部署完整指南

**项目**: 老年人护理监测系统 - 基线学习与个性化信号  
**版本**: 1.0  
**日期**: April 2026  
**状态**: ✅ 就绪部署

---

## 📋 文档导航

这个部署包包含以下文件，请按顺序阅读：

### 1. 📖 核心集成文档（先读这些）

| 文件 | 用途 | 阅读时间 |
|-----|------|---------|
| **BASELINE_UI_INTEGRATION_GUIDE.md** | 架构设计和集成概览 | 20分钟 |
| **INTEGRATION_CODE_SNIPPETS.md** | 8个ready-to-use代码片段 | 15分钟 |

### 2. 🛠️ 实施指南（部署时查阅）

| 文件 | 用途 | 阅读时间 |
|-----|------|---------|
| **IMPLEMENTATION_STEP_BY_STEP.md** | 详细的分步实施指南（推荐） | 45分钟 |
| **QUICK_DEPLOY.sh** | 自动化部署脚本 | 5分钟 |

### 3. ✅ 质量保证（测试和验证）

| 文件 | 用途 | 阅读时间 |
|-----|------|---------|
| **TESTING_GUIDE.md** | 完整的单元测试、集成测试、E2E测试 | 30分钟 |
| **DEPLOYMENT_CHECKLIST.md** | 部署前检查清单（必读） | 15分钟 |

---

## 🚀 快速开始（5分钟）

如果你已经了解系统设计，可以直接运行自动化部署：

```bash
# 1. 赋予脚本执行权限
chmod +x QUICK_DEPLOY.sh

# 2. 运行自动化部署
./QUICK_DEPLOY.sh

# 3. 按提示完成部署
```

脚本会自动完成以下操作：
- ✅ 检查环境（Node.js, PostgreSQL）
- ✅ 备份数据库
- ✅ 运行迁移
- ✅ 安装依赖
- ✅ 验证代码
- ✅ 构建项目
- ✅ 测试API

---

## 📖 详细部署流程（推荐）

如果是第一次部署，建议按照这个流程：

### 第1阶段：理解系统（30分钟）

```bash
# 1. 阅读架构文档
cat BASELINE_UI_INTEGRATION_GUIDE.md | head -100

# 2. 查看代码结构
ls -la src/lib/statusEngineV2.ts
ls -la src/components/EnhancedStatusView.tsx

# 3. 理解集成点
grep -n "generateStatusViewWithBaseline" INTEGRATION_CODE_SNIPPETS.md
```

**关键概念**:
- **Baseline Learning**: 每日滚动平均（15%新数据，85%历史）
- **Personalized Signals**: 基于baseline的偏差检测
- **Temporary Condition**: ≥3天异常状态检测和学习门控
- **Universal Rules**: 始终优先于个性化信号

### 第2阶段：准备环境（15分钟）

```bash
# 1. 检查依赖
node --version    # 应该 ≥ 16.x
npm --version     # 应该 ≥ 8.x
psql --version    # PostgreSQL 12+

# 2. 备份数据库（生产必须）
pg_dump -U postgres your_db > backup_$(date +%Y%m%d).sql

# 3. 安装项目依赖
npm install
```

### 第3阶段：执行部署（1-2小时）

按照 `IMPLEMENTATION_STEP_BY_STEP.md` 的阶段部署：

```bash
# 阶段1: 数据库迁移
npm run migrate:up

# 阶段2: 验证API端点
curl http://localhost:3000/api/elders/elder_1/status

# 阶段3: 启动定时任务
# (在应用启动时自动初始化)

# 阶段4: 测试UI
npm run dev
# 访问 http://localhost:3000/elders/elder_1
```

### 第4阶段：测试和验证（1小时）

```bash
# 运行完整测试套件
npm test

# 验证部署清单
cat DEPLOYMENT_CHECKLIST.md | grep "^\- \["

# 检查监控
curl http://localhost:3000/api/admin/metrics/baseline
```

### 第5阶段：生产部署（30分钟）

```bash
# 构建生产版本
npm run build

# 启动生产服务
npm run start

# 验证生产API
curl https://your-domain.com/api/elders/elder_1/status

# 监视日志
tail -f logs/production.log | grep baseline
```

---

## 📊 系统架构概览

```
数据源（传感器事件）
    ↓
statusEngineV2.ts（每日处理）
    ├─ 1️⃣ 检测临时状态（≥3天异常）
    ├─ 2️⃣ 决定是否学习（排除高风险日期）
    ├─ 3️⃣ 更新baseline（滚动平均）
    ├─ 4️⃣ 生成个性化信号（基于偏差）
    └─ 5️⃣ 合并通用规则（优先级更高）
    ↓
API端点 (/api/elders/[id]/status)
    ↓
React组件 (EnhancedStatusView)
    ├─ 显示通用风险（最小基准）
    ├─ 显示个性化信号（补充）
    ├─ 显示baseline进度（学习状态）
    └─ 显示临时状态（异常模式）
```

---

## 🔑 关键设计原则

### ✅ 安全第一
```
通用规则永远优先 > 个性化信号是补充

如果universal_risk === 'high' → 显示高风险警报
即使baseline显示低活动，也不会削弱警报
```

### ✅ 智能学习
```
学习来源: 仅稳定日期 + 非高风险日期 + 非临时状态

排除条件:
- 临时状态活跃（≥3天异常）
- 高风险日期（任何高风险事件）
- Baseline需审查状态
```

### ✅ 告警控制
```
高风险事件: 100%通过（永不抑制）
例行事件:   概率抑制（70-50% 通过率）
临时状态:   保留关键告警，降低例行频率
```

---

## 📈 部署时间表

| 阶段 | 任务 | 时间 | 状态 |
|------|-----|------|------|
| 准备 | 备份、检查环境 | 15分钟 | ⬜ |
| 数据库 | 迁移、初始化 | 10分钟 | ⬜ |
| 代码 | 部署核心文件、API | 15分钟 | ⬜ |
| 测试 | 单元测试、集成测试 | 30分钟 | ⬜ |
| UI | 替换组件、测试 | 15分钟 | ⬜ |
| 定时任务 | 设置cron、验证 | 10分钟 | ⬜ |
| 验证 | 完整E2E测试 | 20分钟 | ⬜ |
| 生产 | 构建、启动、监控 | 30分钟 | ⬜ |
| **总计** | | **2-3小时** | |

---

## ⚠️ 常见问题

### Q: 基线什么时候开始学习？
**A**: 立即开始。首次系统会标记为`collecting`状态，7天内会累积足够数据，然后自动变为`active`状态。

### Q: 现有elder的历史数据怎么办？
**A**: 迁移脚本会初始化所有现有elder为`collecting`状态，从迁移日期开始计算。可以选择手动设置为`active`用于测试。

### Q: 个性化信号会替代高风险告警吗？
**A**: **绝不会**。设计中通用规则是最小基准，个性化信号仅提供补充背景。任何高风险事件都会显示。

### Q: 如果baseline学错了怎么办？
**A**: 如果连续异常≥3天，系统自动标记为`needs_review`并停止学习。管理员可手动审查并重置。

### Q: 性能如何？
**A**: 
- 单个elder状态生成: < 100ms
- 1000个elder日常更新: < 5秒（并行）
- API响应: 95% < 1s, 99% < 3s

---

## 🔄 持续集成/部署 (CI/CD)

### GitHub Actions示例

```yaml
# .github/workflows/deploy.yml
name: Deploy Baseline Learning

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm install
      
      - name: Run tests
        run: npm test
      
      - name: Build
        run: npm run build
      
      - name: Deploy
        run: npm run deploy
```

---

## 📞 故障排除快速参考

### 问题: API返回500错误
```bash
# 检查数据库连接
psql -d your_db -c "SELECT 1;"

# 检查baseline初始化
psql -d your_db -c "SELECT elder_id, baseline IS NULL FROM elders LIMIT 5;"

# 查看详细错误
curl -v http://localhost:3000/api/elders/elder_1/status
```

### 问题: 定时任务不执行
```bash
# 检查日志
grep "baseline update" logs/*.log

# 验证时区设置
date; date -u

# 临时改为每分钟测试
# 在 baselineScheduler.ts: cron.schedule('* * * * *', ...)
```

### 问题: 个性化信号不显示
```typescript
// 检查baseline状态
SELECT baseline->>'baseline_status', baseline->>'baseline_days_collected'
FROM elders WHERE elder_id = 'elder_1';

// 应该是: active 且 ≥ 7
```

---

## 📚 相关文档

- [系统架构](BASELINE_UI_INTEGRATION_GUIDE.md)
- [代码片段](INTEGRATION_CODE_SNIPPETS.md)
- [分步部署](IMPLEMENTATION_STEP_BY_STEP.md)
- [完整检查清单](DEPLOYMENT_CHECKLIST.md)
- [测试指南](TESTING_GUIDE.md)

---

## ✨ 部署后的优化项

### 短期（部署后1周）
- [ ] 监视baseline收集率（目标: 95%达到active）
- [ ] 验证告警准确率（目标: >90%真阳性）
- [ ] 用户培训和反馈
- [ ] 文档更新

### 中期（部署后1个月）
- [ ] 实时baseline更新（从每日改为每小时）
- [ ] 添加基线可视化（学习曲线图表）
- [ ] 高级机器学习检测
- [ ] 护理人员基线调整工具

### 长期（部署后3个月）
- [ ] 多维度基线（工作日vs周末, 季节变化）
- [ ] 预测性告警（基于趋势）
- [ ] 自适应告警阈值
- [ ] 跨elder学习池

---

## 📞 支持和维护

部署完成后，请配置：

1. **监控告警**
   - Baseline收集进度
   - API响应时间
   - 错误率
   - 数据库性能

2. **日志聚合**
   - 集中日志收集
   - 错误日志告警
   - 审计日志

3. **团队培训**
   - 开发人员：架构和代码
   - QA：测试流程
   - 运维：监控和告警
   - 最终用户：功能和界面

---

## 🎯 成功标志

部署成功的标志：

- ✅ 所有测试通过（>80%代码覆盖率）
- ✅ API响应时间 < 1秒（95%）
- ✅ 95%的elder在7天内达到`active`状态
- ✅ 个性化信号出现率 > 50%
- ✅ 告警准确率 > 90%
- ✅ 没有关键错误在日志中
- ✅ 监控面板正常工作
- ✅ 用户反馈积极

---

## 📝 版本历史

| 版本 | 日期 | 更新 |
|------|------|------|
| 1.0 | Apr 2026 | 初始发布 |

---

## 许可证和归属

本项目为内部开发，遵循公司政策。

---

**祝部署顺利！🚀**

如有问题，请查看对应的详细文档或联系开发团队。

---

**快速链接**:
- 🏗️ [架构详解](BASELINE_UI_INTEGRATION_GUIDE.md)
- 💻 [代码示例](INTEGRATION_CODE_SNIPPETS.md)
- 🛠️ [分步指南](IMPLEMENTATION_STEP_BY_STEP.md)
- ✅ [检查清单](DEPLOYMENT_CHECKLIST.md)
- 🧪 [测试指南](TESTING_GUIDE.md)

---

**最后更新**: April 26, 2026 | **维护者**: 系统团队
