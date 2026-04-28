# 多传感器闭环异常检测系统集成指南

## 📡 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    硬件设备层                                  │
├─────────┬─────────┬──────────┬──────────────────────────────┤
│   FP2   │  Sleep  │   Door   │      Hallway PIR/Radar      │
│         │ Tracker │ Sensor   │                              │
└────┬────┴────┬────┴────┬─────┴────────┬────────────────────┘
     │         │         │              │
     └─────────┴─────────┴──────────────┘
              │ 传感器数据
     ┌────────▼──────────────────────────┐
     │   Sensor Fusion Engine             │
     │ (sensorFusion.ts)                  │
     │                                    │
     │ - NO_ACTIVITY智能判断              │
     │ - NIGHT_BED_EXIT检测               │
     │ - PATH_INTERRUPTED分析             │
     │ - MEDICATION多状态判断             │
     │ - BATHROOM_RISK提升                │
     └────────┬──────────────────────────┘
              │ 异常事件
     ┌────────▼──────────────────────────┐
     │   Alert Pipeline                   │
     │ (alertPipeline.ts)                 │
     │                                    │
     │ - Debounce (60秒)                  │
     │ - Cooldown (30分钟)                │
     │ - Quiet Mode (22:00-07:00)         │
     └────────┬──────────────────────────┘
              │ 去重后的警报
     ┌────────▼──────────────────────────┐
     │   Confidence & Evidence            │
     │ (confidenceScorer.ts)              │
     │                                    │
     │ - 计算置信度分数                   │
     │ - 生成证据标签                     │
     └────────┬──────────────────────────┘
              │
     ┌────────▼──────────────────────────┐
     │   用户展示层                       │
     │ (behaviorText.ts)                  │
     │                                    │
     │ "Likely issue detected"            │
     │ "Possible change detected"         │
     │ "No concern"                       │
     └────────────────────────────────────┘
```

---

## 🔧 集成步骤

### Step 1: 添加传感器数据结构

已完成：`src/types/sensor.ts`
- ✅ FP2SensorData
- ✅ SleepTrackerData
- ✅ DoorSensorData
- ✅ HallwaySensorData
- ✅ SensorSnapshot (快照)
- ✅ AnomalyEvent (输出)

### Step 2: 实现传感器融合引擎

已完成：`src/lib/sensorFusion.ts`

**五大智能判断：**

```typescript
// 1. 无活动智能判断
analyzeNoActivityAnomalies(snapshot, history, inactivity_minutes)
// 返回：{ anomaly_type, risk_level, confidence_score, evidence_sources }

// 2. 夜间离床未回
analyzeNightBedExitNoReturn(snapshot, max_out_of_bed_minutes)

// 3. 路径中断
analyzePathInterrupted(snapshot, max_transit_seconds)

// 4. 用药相关
analyzeMedicationAnomalies(snapshot, history, medication_hours)
// 返回3种异常：
// - medication_cabinet_accessed
// - medication_window_missed  
// - medication_access_without_followup

// 5. 卫生间风险提升
analyzeBathroomRiskElevation(snapshot, history, extended_minutes)
```

### Step 3: 配置参数

已完成：`src/config/sensorConfig.ts`

**关键参数：**
```typescript
// FP2
fp2_inactivity_threshold: 120分钟

// Sleep Tracker
night_bed_exit_threshold: 10分钟
night_hours: 22:00-07:00

// Door Sensor
medication_typical_hours: [8, 12, 18]
medication_followup_window: 600秒（10分钟）

// Hallway
expected_transit_time: 90秒

// Bathroom
bathroom_long_stay: 20分钟
bathroom_exit_timeout: 30分钟

// 多信号确认
multi_signal_min_count: 2个信号
```

### Step 4: 集成到现有系统

**修改 statusEngine.ts：**

```typescript
import { analyzeAllAnomalies } from '@/lib/sensorFusion';
import { SensorSnapshot } from '@/types/sensor';
import { SENSOR_CONFIG } from '@/config/sensorConfig';

// 在 generateStatusViewModel 中调用：
const sensorSnapshot: SensorSnapshot = {
  timestamp: new Date().toISOString(),
  fp2: getCurrentFP2Data(),
  sleep_tracker: getCurrentSleepTrackerData(),
  door_sensor: getCurrentDoorSensorData(),
  hallway_sensor: getCurrentHallwaySensorData(),
  data_completeness: { /* ... */ }
};

const sensorHistory: SensorHistory = {
  last_hour: getLastHourSnapshots(),
  last_24h_summary: get24hSummary(),
  last_7days_pattern: get7DaysPattern()
};

// 分析所有异常
const anomalies = analyzeAllAnomalies(
  sensorSnapshot,
  sensorHistory,
  {
    fp2_inactivity_minutes: SENSOR_CONFIG.fp2.inactivity_threshold_minutes,
    night_bed_exit_minutes: SENSOR_CONFIG.sleep_tracker.night_bed_exit_threshold_minutes,
    path_interrupted_seconds: SENSOR_CONFIG.hallway.expected_transit_time_seconds,
    bathroom_extended_minutes: SENSOR_CONFIG.sensor.bathroom_long_stay_minutes,
    medication_hours: SENSOR_CONFIG.door_sensor.medication_typical_hours,
  }
);

// 传递到现有的 alert pipeline
for (const anomaly of anomalies) {
  const shouldAlert = shouldPushAlert(
    convertAnomalyToBehaviorEvent(anomaly),
    anomaly.evidence_sources.length
  );
  
  if (shouldAlert) {
    // 添加到 statusViewModel.primary_alert
  }
}
```

---

## 🎯 五大异常检测详解

### 1️⃣ NO_ACTIVITY（无活动智能判断）

**问题：** 不能只根据FP2无活动就报警（误报率高）

**解决方案：** 多信号组合确认

```
条件组合：

┌─ 入户门是否关闭？
├─ 床垫是否有人？
├─ 最近5分钟有走廊经过吗？
└─ FP2 检测到活动？

┌────────────────────────────────────────────────┐
│  组合1: 门关 + 床有人 + 无passage              │
│  → 无异常 (睡眠状态)                            │
│  → confidence: 0                               │
├────────────────────────────────────────────────┤
│  组合2: 门关 + 无passage + 无活动               │
│  → 低风险 (可能休息)                            │
│  → confidence: 0.3 → 0.4                       │
├────────────────────────────────────────────────┤
│  组合3: 门打开 + 无passage + 无活动             │
│  → 高风险 (真实异常)                            │
│  → confidence: 0.85 → risk_level: HIGH         │
└────────────────────────────────────────────────┘

证据来源：
- sensor:door_closed
- sensor:bed_presence
- sensor:no_recent_passage
- sensor:no_fp2_activity
- inference:confirmed_no_activity
```

### 2️⃣ NIGHT_BED_EXIT_NO_RETURN（夜间离床未回）

**问题：** 夜间离床可能跌倒或需要帮助

**检测条件：**
```
✓ 当前是夜间 (22:00-07:00)
✓ Sleep tracker 显示离床
✓ 离床时长 > 10 分钟
✓ 没有 FP2 活动（可能跌倒）

风险等级判断：
- 离床 10-20 分钟 + 有活动 → attention (confidence: 0.6)
- 离床 20+ 分钟 + 无活动 → high (confidence: 0.85)
```

### 3️⃣ PATH_INTERRUPTED（路径中断）

**问题：** 走廊检测到经过，但老人长时间未到达目的地

**检测逻辑：**
```
时序分析：
- T0: Hallway sensor 检测到经过
- T0+90秒: 应该在卧室/客厅/卫生间出现
- T0+90秒: 如果 FP2 无活动

可能原因：
- 停留在走廊
- 跌倒
- 传感器故障

风险等级：
- 经过后 90-180 秒未到达 → attention (confidence: 0.5-0.65)
- 经过后 >3 分钟未到达 + 无活动 → high (confidence: 0.8)
```

### 4️⃣ MEDICATION（用药多状态）

**三种异常类型：**

```typescript
1. medication_cabinet_accessed
   - 何时: 药柜刚打开（<60秒）
   - 风险: normal
   - 置信度: 0.95
   - 证据: sensor:medication_cabinet_open

2. medication_window_missed
   - 何时: 预设用药时间（8:00, 12:00, 18:00）但未打开药柜
   - 风险: attention
   - 置信度: 0.65
   - 证据: context:medication_time, sensor:cabinet_not_accessed

3. medication_access_without_followup
   - 何时: 打开药柜后 10 分钟内无进食活动
   - 风险: attention
   - 置信度: 0.6（单信号）
   - 证据: sensor:medication_cabinet_open, sensor:no_eating_activity
   - 说明: 只有单一信号，置信度低，需观察
```

### 5️⃣ BATHROOM_RISK（卫生间风险）

**单一信号不触发高风险，需多信号：**

```
风险提升条件：

┌─ 卫生间停留 > 20 分钟 (单信号)
│
├─ 信号1: 走廊无经过 (未离开迹象)
│ → 多信号确认 → risk_level: high
│
└─ 信号2: 夜间时段
  → 多信号确认 → risk_level: high

置信度计算：
- 单一停留信号 → 0.4
- + 无走廊经过 → 0.6
- + 夜间 → 0.75+ (risk_level: high)
```

---

## 📊 置信度评分规则

```
单信号（1个证据）
├─ 范围: 0.4 - 0.6
├─ 例: 只有 "bathroom_long_stay"
└─ 说明: "We're somewhat uncertain"

双信号（2个证据）
├─ 范围: 0.6 - 0.8
├─ 例: "bathroom_long_stay" + "no_passage"
└─ 说明: "We're fairly confident"

多信号+时间上下文（3+个证据）
├─ 范围: 0.8 - 0.95
├─ 例: "bathroom_long_stay" + "no_passage" + "nighttime"
└─ 说明: "We're very confident"

High Risk Boost
├─ 加成: +15%
├─ 条件: 有明确的高风险指标
└─ 效果: 0.6 → 0.75
```

---

## 🚦 Alert Pipeline 与 Sensor Fusion 的关系

```
Sensor Fusion                Alert Pipeline
(检测异常)                   (去重和优化)

AnomalyEvent
  ├─ anomaly_type
  ├─ confidence_score      shouldPushAlert?
  ├─ evidence_sources  ─────────►  ├─ Debounce (60秒)
  └─ risk_level                     ├─ Multi-signal (≥2)
                                    ├─ Cooldown (30分钟)
                                    └─ Quiet Mode
                                        │
                                        ▼
                                    最终推送决策
```

---

## 💡 关键设计原则

✅ **单一信号默认不触发高风险**
- 需要多个传感器证据的组合
- 例外：high risk 事件仍然立即推送

✅ **每个判断都返回 confidence_score**
- 0-1 范围
- 用户可以看到系统的确定性程度

✅ **每个事件都有 evidence_sources**
- 可追踪：为什么判断这个异常
- 可解释：对用户透明

✅ **不做医疗诊断**
- 只提示风险
- 用词温和："Possible", "Likely", "No concern"

✅ **不改 API，不改 UI**
- 纯逻辑层优化
- 向后兼容

---

## 📋 实现清单

- ✅ `src/types/sensor.ts` - 传感器数据类型
- ✅ `src/lib/sensorFusion.ts` - 五大异常检测
- ✅ `src/config/sensorConfig.ts` - 配置和参数

**待集成：**
- ⏳ 修改 `statusEngine.ts` - 调用 sensorFusion
- ⏳ 映射现有 BehaviorEvent 到 AnomalyEvent
- ⏳ 更新数据流程以支持传感器输入

---

## 🔗 API 映射

现有系统中 BehaviorEvent 的 event_type 映射到新异常类型：

```typescript
// 旧的 event_type          // 新的 anomaly_type
'no_activity'          → 'no_activity_confirmed' (多信号)
'night_wake'           → 'night_bed_exit_no_return'
'bathroom_long_stay'   → 'bathroom_risk_elevated'
// 新增：
                       → 'path_interrupted'
                       → 'medication_cabinet_accessed'
                       → 'medication_window_missed'
                       → 'medication_access_without_followup'
```

---

## 🎓 示例：如何调用

```typescript
import { analyzeAllAnomalies } from '@/lib/sensorFusion';
import { SENSOR_CONFIG } from '@/config/sensorConfig';

// 获取当前传感器快照
const snapshot: SensorSnapshot = {
  timestamp: new Date().toISOString(),
  fp2: fp2Data,
  sleep_tracker: sleepData,
  door_sensor: doorData,
  hallway_sensor: hallwayData,
  data_completeness: { /* 可用性 */ }
};

// 获取历史数据（用于趋势分析）
const history = getHistoricalData();

// 运行融合分析
const anomalies = analyzeAllAnomalies(
  snapshot,
  history,
  {
    fp2_inactivity_minutes: SENSOR_CONFIG.fp2.inactivity_threshold_minutes,
    medication_hours: SENSOR_CONFIG.door_sensor.medication_typical_hours,
    // ... 其他参数
  }
);

// 处理结果
for (const anomaly of anomalies) {
  console.log(`发现异常: ${anomaly.anomaly_type}`);
  console.log(`置信度: ${anomaly.confidence_score}`);
  console.log(`风险: ${anomaly.risk_level}`);
  console.log(`证据: ${anomaly.evidence_sources.join(', ')}`);
  
  // 传递到 alert pipeline
  if (shouldPushAlert(convertToEvent(anomaly), anomaly.evidence_sources.length)) {
    // 显示给用户
  }
}
```

