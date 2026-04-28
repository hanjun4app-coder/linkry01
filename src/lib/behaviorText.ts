import {
  BehaviorEvent,
  BehaviorText,
  DailyBehaviorSummaryInput,
  DailySummaryText,
  RiskLevel,
} from '@/types/behavior';

/**
 * 将行为事件转换为家属可理解的展示文案
 * 支持英文和中文，默认英文（美国市场）
 *
 * @param event - 行为事件数据
 * @param language - 语言（默认 'en'）
 * @returns 展示文案，包括证据来源
 */
export function generateBehaviorText(
  event: BehaviorEvent,
  language: 'en' | 'zh' = 'en'
): BehaviorText {
  const duration = event.duration_minutes ?? 0;
  const isDuration = duration > 0;

  // 定义所有事件类型的文案结构
  const textMap: Record<
    string,
    {
      en: Record<RiskLevel | 'default', Omit<BehaviorText, 'event_id'>>;
      zh: Record<RiskLevel | 'default', Omit<BehaviorText, 'event_id'>>;
    }
  > = {
    // 起床事件
    wake_up: {
      en: {
        normal: {
          title: 'Woken up',
          summary: 'Your loved one has started their day.',
          detail: 'Activity detected in the main areas.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: 'Woken up',
          summary: 'Your loved one has started their day.',
          detail: 'Activity detected in the main areas.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: 'Woken up',
          summary: 'Your loved one has started their day.',
          detail: 'Activity detected in the main areas.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: 'Woken up',
          summary: 'Your loved one has started their day.',
          detail: 'Activity detected in the main areas.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
      zh: {
        normal: {
          title: '已起床',
          summary: '老人今天已开始活动。',
          detail: '系统检测到老人从卧室进入活动区域。',
          suggestion: '当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: '已起床',
          summary: '老人今天已开始活动。',
          detail: '系统检测到老人从卧室进入活动区域。',
          suggestion: '当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: '已起床',
          summary: '老人今天已开始活动。',
          detail: '系统检测到老人从卧室进入活动区域。',
          suggestion: '当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: '已起床',
          summary: '老人今天已开始活动。',
          detail: '系统检测到老人从卧室进入活动区域。',
          suggestion: '当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
    },

    // 客厅活动事件
    living_activity: {
      en: {
        normal: {
          title: 'Active',
          summary: 'Your loved one is up and active.',
          detail: 'Continuous activity detected in common areas.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: 'Active',
          summary: 'Your loved one is up and active.',
          detail: 'Continuous activity detected in common areas.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: 'Active',
          summary: 'Your loved one is up and active.',
          detail: 'Continuous activity detected in common areas.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: 'Active',
          summary: 'Your loved one is up and active.',
          detail: 'Continuous activity detected in common areas.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
      zh: {
        normal: {
          title: '正常活动',
          summary: '老人正在活动。',
          detail: '系统检测到老人在活动区域持续活动。',
          suggestion: '当前状态正常。',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: '正常活动',
          summary: '老人正在活动。',
          detail: '系统检测到老人在活动区域持续活动。',
          suggestion: '当前状态正常。',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: '正常活动',
          summary: '老人正在活动。',
          detail: '系统检测到老人在活动区域持续活动。',
          suggestion: '当前状态正常。',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: '正常活动',
          summary: '老人正在活动。',
          detail: '系统检测到老人在活动区域持续活动。',
          suggestion: '当前状态正常。',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
    },

    // 卫生间使用事件
    bathroom_use: {
      en: {
        normal: {
          title: 'Bathroom visit',
          summary: 'Bathroom activity detected.',
          detail: 'This is a normal bathroom use record.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: 'Bathroom visit',
          summary: 'Bathroom activity detected.',
          detail: 'This is a normal bathroom use record.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: 'Bathroom visit',
          summary: 'Bathroom activity detected.',
          detail: 'This is a normal bathroom use record.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: 'Bathroom visit',
          summary: 'Bathroom activity detected.',
          detail: 'This is a normal bathroom use record.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
      zh: {
        normal: {
          title: '卫生间使用',
          summary: '检测到老人进入卫生间。',
          detail: '这是一次普通的卫生间使用记录。',
          suggestion: '当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: '卫生间使用',
          summary: '检测到老人进入卫生间。',
          detail: '这是一次普通的卫生间使用记录。',
          suggestion: '当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: '卫生间使用',
          summary: '检测到老人进入卫生间。',
          detail: '这是一次普通的卫生间使用记录。',
          suggestion: '当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: '卫生间使用',
          summary: '检测到老人进入卫生间。',
          detail: '这是一次普通的卫生间使用记录。',
          suggestion: '当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
    },

    // 卫生间停留过久事件（最关键的事件，需要风险区分）
    bathroom_long_stay: {
      en: {
        high: {
          title: 'Likely issue detected: Extended bathroom visit',
          summary:
            'Your loved one has been in the bathroom longer than usual.',
          detail: isDuration
            ? `Bathroom visit has lasted about ${duration} minutes.`
            : 'Bathroom visit has lasted longer than expected.',
          suggestion: 'A quick phone call would be good to make sure everything is okay.',
          display_level: 'high',
          evidence_sources: ['safety_rule:bathroom_duration'],
        },
        attention: {
          title: 'Possible change detected: Bathroom visit',
          summary:
            'Your loved one has been in the bathroom longer than usual.',
          detail: isDuration
            ? `Bathroom visit has lasted about ${duration} minutes.`
            : 'Bathroom visit has lasted longer than expected.',
          suggestion: 'No urgent action needed, but a gentle check-in is a good idea.',
          display_level: 'attention',
          evidence_sources: ['safety_rule:bathroom_duration'],
        },
        normal: {
          title: 'Extended bathroom visit',
          summary:
            'Your loved one has been in the bathroom for a bit longer than usual.',
          detail: isDuration
            ? `Bathroom visit has lasted about ${duration} minutes.`
            : 'Bathroom visit has lasted longer than expected.',
          suggestion: 'Consider a gentle phone check-in if this continues.',
          display_level: 'attention',
          evidence_sources: ['safety_rule:bathroom_duration'],
        },
        default: {
          title: 'Extended bathroom visit',
          summary:
            'Your loved one has been in the bathroom for a bit longer than usual.',
          detail: isDuration
            ? `Bathroom visit has lasted about ${duration} minutes.`
            : 'Bathroom visit has lasted longer than expected.',
          suggestion: 'Consider a gentle phone check-in if this continues.',
          display_level: 'attention',
          evidence_sources: ['safety_rule:bathroom_duration'],
        },
      },
      zh: {
        high: {
          title: '卫生间停留过久',
          summary: '老人已在卫生间停留较长时间，可能需要关注。',
          detail: isDuration
            ? `卫生间停留已持续约 ${duration} 分钟。`
            : '卫生间停留时间超出预期。',
          suggestion: '建议立即联系老人或附近联系人确认情况。',
          display_level: 'high',
          evidence_sources: ['safety_rule:bathroom_duration'],
        },
        attention: {
          title: '卫生间停留较长',
          summary: '老人卫生间停留时间较长。',
          detail: isDuration
            ? `已在卫生间停留约 ${duration} 分钟。`
            : '卫生间停留时间超出预期。',
          suggestion: '建议电话确认老人状态。',
          display_level: 'attention',
          evidence_sources: ['safety_rule:bathroom_duration'],
        },
        normal: {
          title: '卫生间停留较长',
          summary: '老人卫生间停留时间较长。',
          detail: isDuration
            ? `已在卫生间停留约 ${duration} 分钟。`
            : '卫生间停留时间超出预期。',
          suggestion: '建议电话确认老人状态。',
          display_level: 'attention',
          evidence_sources: ['safety_rule:bathroom_duration'],
        },
        default: {
          title: '卫生间停留较长',
          summary: '老人卫生间停留时间较长。',
          detail: isDuration
            ? `已在卫生间停留约 ${duration} 分钟。`
            : '卫生间停留时间超出预期。',
          suggestion: '建议电话确认老人状态。',
          display_level: 'attention',
          evidence_sources: ['safety_rule:bathroom_duration'],
        },
      },
    },

    // 长时间无活动事件（高风险事件）
    no_activity: {
      en: {
        high: {
          title: 'Likely issue detected: No recent activity',
          summary:
            "We haven't detected any activity for a while. It's a good time to check in.",
          detail: isDuration
            ? `No activity has been detected for approximately ${duration} minutes.`
            : 'No activity has been detected for an extended period.',
          suggestion: 'A phone call to check in would be a good idea.',
          display_level: 'high',
          evidence_sources: ['safety_rule:long_inactivity', 'pattern:low_activity'],
        },
        attention: {
          title: 'Possible change detected: Lower activity than usual',
          summary:
            'We notice less activity than typical. A gentle check-in could be nice.',
          detail: isDuration
            ? `No clear activity detected for approximately ${duration} minutes.`
            : 'No clear activity detected for a while.',
          suggestion: 'A casual phone call whenever convenient would be fine.',
          display_level: 'attention',
          evidence_sources: ['safety_rule:long_inactivity', 'pattern:low_activity'],
        },
        normal: {
          title: 'Minimal activity',
          summary:
            'We notice minimal activity. A gentle check-in might be good.',
          detail: isDuration
            ? `No clear activity detected for approximately ${duration} minutes.`
            : 'No clear activity detected for a while.',
          suggestion: 'Consider reaching out with a phone call.',
          display_level: 'attention',
          evidence_sources: ['safety_rule:long_inactivity', 'pattern:low_activity'],
        },
        default: {
          title: 'Minimal activity',
          summary:
            'We notice minimal activity. A gentle check-in might be good.',
          detail: isDuration
            ? `No clear activity detected for approximately ${duration} minutes.`
            : 'No clear activity detected for a while.',
          suggestion: 'Consider reaching out with a phone call.',
          display_level: 'attention',
          evidence_sources: ['safety_rule:long_inactivity', 'pattern:low_activity'],
        },
      },
      zh: {
        high: {
          title: '长时间未活动',
          summary: '系统长时间未检测到活动，建议尽快确认。',
          detail: isDuration
            ? `已连续约 ${duration} 分钟未检测到活动。`
            : '已连续较长时间未检测到活动。',
          suggestion: '建议立即电话联系老人确认状态。',
          display_level: 'high',
          evidence_sources: ['safety_rule:long_inactivity', 'pattern:low_activity'],
        },
        attention: {
          title: '长时间无活动',
          summary: '系统较长时间未检测到明显活动。',
          detail: isDuration
            ? `已连续约 ${duration} 分钟未检测到活动。`
            : '已连续较长时间未检测到活动。',
          suggestion: '建议稍后关注，必要时电话确认。',
          display_level: 'attention',
          evidence_sources: ['safety_rule:long_inactivity', 'pattern:low_activity'],
        },
        normal: {
          title: '长时间无活动',
          summary: '系统较长时间未检测到明显活动。',
          detail: isDuration
            ? `已连续约 ${duration} 分钟未检测到活动。`
            : '已连续较长时间未检测到活动。',
          suggestion: '建议稍后关注，必要时电话确认。',
          display_level: 'attention',
          evidence_sources: ['safety_rule:long_inactivity', 'pattern:low_activity'],
        },
        default: {
          title: '长时间无活动',
          summary: '系统较长时间未检测到明显活动。',
          detail: isDuration
            ? `已连续约 ${duration} 分钟未检测到活动。`
            : '已连续较长时间未检测到活动。',
          suggestion: '建议稍后关注，必要时电话确认。',
          display_level: 'attention',
          evidence_sources: ['safety_rule:long_inactivity', 'pattern:low_activity'],
        },
      },
    },

    // 夜间起床事件
    night_wake: {
      en: {
        normal: {
          title: 'Possible change detected: Nighttime activity',
          summary: 'Your loved one got up during the night.',
          detail:
            'Activity detected outside the bedroom during nighttime hours.',
          suggestion:
            'Not a concern if this is occasional. If it happens often, a gentle check-in is fine.',
          display_level: 'attention',
          evidence_sources: ['time_context:night', 'safety_rule:night_activity'],
        },
        attention: {
          title: 'Possible change detected: Nighttime activity',
          summary: 'Your loved one got up during the night.',
          detail:
            'Activity detected outside the bedroom during nighttime hours.',
          suggestion:
            'Not a concern if this is occasional. If it happens often, a gentle check-in is fine.',
          display_level: 'attention',
          evidence_sources: ['time_context:night', 'safety_rule:night_activity'],
        },
        high: {
          title: 'Possible change detected: Frequent nighttime activity',
          summary: 'Your loved one has been getting up multiple times during the night.',
          detail:
            'Multiple activity periods detected outside the bedroom during nighttime hours.',
          suggestion:
            "If this becomes frequent, a check-in to see how they're sleeping would be helpful.",
          display_level: 'attention',
          evidence_sources: ['time_context:night', 'safety_rule:night_activity'],
        },
        default: {
          title: 'Possible change detected: Nighttime activity',
          summary: 'Your loved one got up during the night.',
          detail:
            'Activity detected outside the bedroom during nighttime hours.',
          suggestion:
            'Not a concern if this is occasional. If it happens often, a gentle check-in is fine.',
          display_level: 'attention',
          evidence_sources: ['time_context:night', 'safety_rule:night_activity'],
        },
      },
      zh: {
        normal: {
          title: '夜间活动',
          summary: '检测到老人夜间起床活动。',
          detail: '夜间检测到从卧室到其他区域的活动。',
          suggestion: '如夜间活动频繁，建议持续关注。',
          display_level: 'attention',
          evidence_sources: ['time_context:night', 'safety_rule:night_activity'],
        },
        attention: {
          title: '夜间活动',
          summary: '检测到老人夜间起床活动。',
          detail: '夜间检测到从卧室到其他区域的活动。',
          suggestion: '如夜间活动频繁，建议持续关注。',
          display_level: 'attention',
          evidence_sources: ['time_context:night', 'safety_rule:night_activity'],
        },
        high: {
          title: '夜间活动',
          summary: '检测到老人夜间起床活动。',
          detail: '夜间检测到从卧室到其他区域的活动。',
          suggestion: '如夜间活动频繁，建议持续关注。',
          display_level: 'attention',
          evidence_sources: ['time_context:night', 'safety_rule:night_activity'],
        },
        default: {
          title: '夜间活动',
          summary: '检测到老人夜间起床活动。',
          detail: '夜间检测到从卧室到其他区域的活动。',
          suggestion: '如夜间活动频繁，建议持续关注。',
          display_level: 'attention',
          evidence_sources: ['time_context:night', 'safety_rule:night_activity'],
        },
      },
    },

    // 午休事件
    nap: {
      en: {
        normal: {
          title: 'Resting',
          summary: 'Your loved one is taking a rest.',
          detail: 'Activity in the bedroom area suggests a nap or rest period.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: 'Resting',
          summary: 'Your loved one is taking a rest.',
          detail: 'Activity in the bedroom area suggests a nap or rest period.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: 'Resting',
          summary: 'Your loved one is taking a rest.',
          detail: 'Activity in the bedroom area suggests a nap or rest period.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: 'Resting',
          summary: 'Your loved one is taking a rest.',
          detail: 'Activity in the bedroom area suggests a nap or rest period.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
      zh: {
        normal: {
          title: '午休',
          summary: '老人午间有休息行为。',
          detail: '系统检测到老人中午在卧室区域停留休息。',
          suggestion: '当前状态正常。',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: '午休',
          summary: '老人午间有休息行为。',
          detail: '系统检测到老人中午在卧室区域停留休息。',
          suggestion: '当前状态正常。',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: '午休',
          summary: '老人午间有休息行为。',
          detail: '系统检测到老人中午在卧室区域停留休息。',
          suggestion: '当前状态正常。',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: '午休',
          summary: '老人午间有休息行为。',
          detail: '系统检测到老人中午在卧室区域停留休息。',
          suggestion: '当前状态正常。',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
    },

    // 休息事件
    resting: {
      en: {
        normal: {
          title: 'Resting',
          summary: 'Your loved one appears to be resting.',
          detail: 'Prolonged activity in the bedroom suggests rest or sleep.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: 'Resting',
          summary: 'Your loved one appears to be resting.',
          detail: 'Prolonged activity in the bedroom suggests rest or sleep.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: 'Resting',
          summary: 'Your loved one appears to be resting.',
          detail: 'Prolonged activity in the bedroom suggests rest or sleep.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: 'Resting',
          summary: 'Your loved one appears to be resting.',
          detail: 'Prolonged activity in the bedroom suggests rest or sleep.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
      zh: {
        normal: {
          title: '正在休息',
          summary: '老人目前可能在休息。',
          detail: '系统检测到老人持续停留在卧室区域。',
          suggestion: '当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: '正在休息',
          summary: '老人目前可能在休息。',
          detail: '系统检测到老人持续停留在卧室区域。',
          suggestion: '当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: '正在休息',
          summary: '老人目前可能在休息。',
          detail: '系统检测到老人持续停留在卧室区域。',
          suggestion: '当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: '正在休息',
          summary: '老人目前可能在休息。',
          detail: '系统检测到老人持续停留在卧室区域。',
          suggestion: '当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
    },

    // 离家事件
    left_home: {
      en: {
        normal: {
          title: 'Left home',
          summary: 'Your loved one appears to have left home.',
          detail:
            'The door opened and no activity was detected inside afterward.',
          suggestion:
            'No action needed if they have regular outings planned.',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: 'Left home',
          summary: 'Your loved one appears to have left home.',
          detail:
            'The door opened and no activity was detected inside afterward.',
          suggestion:
            'No action needed if they have regular outings planned.',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: 'Left home',
          summary: 'Your loved one appears to have left home.',
          detail:
            'The door opened and no activity was detected inside afterward.',
          suggestion:
            'No action needed if they have regular outings planned.',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: 'Left home',
          summary: 'Your loved one appears to have left home.',
          detail:
            'The door opened and no activity was detected inside afterward.',
          suggestion:
            'No action needed if they have regular outings planned.',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
      zh: {
        normal: {
          title: '可能离家',
          summary: '系统检测到老人可能已经离开家。',
          detail: '入户门开启后，室内未检测到持续活动。',
          suggestion: '如老人有外出习惯，当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: '可能离家',
          summary: '系统检测到老人可能已经离开家。',
          detail: '入户门开启后，室内未检测到持续活动。',
          suggestion: '如老人有外出习惯，当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: '可能离家',
          summary: '系统检测到老人可能已经离开家。',
          detail: '入户门开启后，室内未检测到持续活动。',
          suggestion: '如老人有外出习惯，当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: '可能离家',
          summary: '系统检测到老人可能已经离开家。',
          detail: '入户门开启后，室内未检测到持续活动。',
          suggestion: '如老人有外出习惯，当前无需处理。',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
    },

    // 回家事件
    returned_home: {
      en: {
        normal: {
          title: 'Returned home',
          summary: 'Your loved one has returned home.',
          detail: 'The door opened and activity was detected inside.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: 'Returned home',
          summary: 'Your loved one has returned home.',
          detail: 'The door opened and activity was detected inside.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: 'Returned home',
          summary: 'Your loved one has returned home.',
          detail: 'The door opened and activity was detected inside.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: 'Returned home',
          summary: 'Your loved one has returned home.',
          detail: 'The door opened and activity was detected inside.',
          suggestion: 'No action needed.',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
      zh: {
        normal: {
          title: '已回家',
          summary: '系统检测到老人回到家中。',
          detail: '入户门开启后，室内重新检测到活动。',
          suggestion: '当前状态正常。',
          display_level: 'normal',
          evidence_sources: [],
        },
        attention: {
          title: '已回家',
          summary: '系统检测到老人回到家中。',
          detail: '入户门开启后，室内重新检测到活动。',
          suggestion: '当前状态正常。',
          display_level: 'normal',
          evidence_sources: [],
        },
        high: {
          title: '已回家',
          summary: '系统检测到老人回到家中。',
          detail: '入户门开启后，室内重新检测到活动。',
          suggestion: '当前状态正常。',
          display_level: 'normal',
          evidence_sources: [],
        },
        default: {
          title: '已回家',
          summary: '系统检测到老人回到家中。',
          detail: '入户门开启后，室内重新检测到活动。',
          suggestion: '当前状态正常。',
          display_level: 'normal',
          evidence_sources: [],
        },
      },
    },
  };

  // 获取事件类型对应的文案
  const eventTypeText = textMap[event.event_type];
  if (!eventTypeText) {
    // 默认情况
    return {
      title: language === 'en' ? 'Status update' : '状态更新',
      summary:
        language === 'en'
          ? 'A new activity has been detected.'
          : '系统检测到新的居家活动。',
      detail:
        language === 'en'
          ? 'No notable issues found.'
          : '当前没有发现明显异常。',
      suggestion:
        language === 'en' ? 'No action needed.' : '当前无需处理。',
      display_level: 'normal' as RiskLevel,
      event_id: event.id,
      evidence_sources: [],
    };
  }

  // 获取对应语言的文案，优先使用 risk_level，否则用 default
  const langText = eventTypeText[language];
  const textByRisk =
    langText[event.risk_level as RiskLevel] || langText['default'];

  return {
    ...textByRisk,
    event_id: event.id,
  };
}

/**
 * 生成今日摘要文案
 * 支持英文和中文，默认英文
 *
 * @param input - 今日行为摘要数据
 * @param language - 语言（默认 'en'）
 * @returns 摘要展示文案
 */
export function generateDailySummaryText(
  input: DailyBehaviorSummaryInput,
  language: 'en' | 'zh' = 'en'
): DailySummaryText {
  const texts = {
    en: {
      high: {
        headline: 'Likely issue detected',
        summary:
          "Today's activity suggests a check-in would be good. Nothing to worry about, just a gentle call to make sure everything is okay.",
        key_points: [
          'Something worth paying attention to',
          `Found ${input.alerts_count} item(s) worth reviewing`,
          'A quick phone call would help',
        ],
        suggestion: 'Consider giving them a call when you have a moment.',
      },
      attention: {
        headline: 'Possible change detected',
        summary:
          "Today's activity was a bit different from usual, but nothing urgent. A casual check-in anytime is fine.",
        key_points: [
          'Some activity differed from the usual pattern',
          `Found ${input.alerts_count} item(s) to keep an eye on`,
          'Feel free to check in whenever convenient',
        ],
        suggestion: 'A casual phone call when you have time would be nice.',
      },
      normal: {
        headline: 'No concern',
        summary:
          'Your loved one had a great day with regular activity. Everything looks normal.',
        key_points: [
          'Regular daily activity detected',
          'Bathroom patterns appeared normal',
          'No unusual quiet periods',
        ],
        suggestion: 'Everything looks good. No action needed.',
      },
    },
    zh: {
      high: {
        headline: '今日存在高风险提醒',
        summary: '系统检测到可能需要立即确认的异常行为。',
        key_points: [
          '存在高风险提醒',
          '建议尽快联系老人或附近联系人',
          `共检测到 ${input.alerts_count} 个需要关注的事项`,
        ],
        suggestion: '建议立即确认老人安全状态。',
      },
      attention: {
        headline: '今日需关注',
        summary: '老人今天出现部分与日常不同的行为，建议家属关注。',
        key_points: [
          '出现需要关注的行为',
          `共检测到 ${input.alerts_count} 个需要关注的事项`,
          '建议查看具体提醒原因',
        ],
        suggestion: '建议电话确认老人状态。',
      },
      normal: {
        headline: '今日状态正常',
        summary: '老人今天有正常活动记录，暂未发现明显异常。',
        key_points: [
          '今日已检测到日常活动',
          '卫生间使用未发现异常',
          '未出现长时间无活动',
        ],
        suggestion: '当前无需处理。',
      },
    },
  };

  const langTexts = texts[language];
  const riskText =
    langTexts[input.highest_risk as RiskLevel] || langTexts.normal;

  return riskText;
}

/**
 * 根据事件确定老人的当前状态标签
 * 支持英文和中文，默认英文
 *
 * @param event - 最新的行为事件
 * @param language - 语言（默认 'en'）
 * @returns 当前状态描述
 */
export function getCurrentStateLabel(
  event: BehaviorEvent,
  language: 'en' | 'zh' = 'en'
): string {
  const zoneLabels = {
    en: {
      bedroom: 'In bedroom',
      living_room: 'In living room',
      bathroom: 'In bathroom',
      entrance: 'At entrance',
      unknown: 'Location unknown',
    },
    zh: {
      bedroom: '在卧室',
      living_room: '在客厅',
      bathroom: '在卫生间',
      entrance: '在门厅',
      unknown: '位置未知',
    },
  };

  const zone = event.zone ?? 'unknown';
  const langLabels = zoneLabels[language];
  return (
    langLabels[zone as keyof typeof langLabels] ||
    (language === 'en' ? 'Active' : '正在活动')
  );
}

/**
 * 判断事件是否应该显示为异常提醒（attention 或 high）
 * @param event - 行为事件
 * @returns true 如果需要显示为提醒
 */
export function isAlertEvent(event: BehaviorEvent): boolean {
  return event.risk_level === 'attention' || event.risk_level === 'high';
}
