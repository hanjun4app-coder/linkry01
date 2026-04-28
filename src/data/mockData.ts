import { BehaviorEvent, DailyBehaviorSummaryInput } from '@/types/behavior';

/**
 * Mock 数据：老人的行为事件
 * 这些事件会被转换为家属友好的展示文案
 */
export const mockBehaviorEvents: BehaviorEvent[] = [
  {
    id: 'event-001',
    home_id: 'home-001',
    event_type: 'wake_up',
    zone: 'bedroom',
    start_time: '2026-04-25T07:30:00',
    risk_level: 'normal',
  },
  {
    id: 'event-002',
    home_id: 'home-001',
    event_type: 'living_activity',
    zone: 'living_room',
    start_time: '2026-04-25T07:45:00',
    duration_minutes: 30,
    risk_level: 'normal',
  },
  {
    id: 'event-003',
    home_id: 'home-001',
    event_type: 'bathroom_use',
    zone: 'bathroom',
    start_time: '2026-04-25T08:15:00',
    duration_minutes: 8,
    risk_level: 'normal',
  },
  {
    id: 'event-004',
    home_id: 'home-001',
    event_type: 'bathroom_long_stay',
    zone: 'bathroom',
    start_time: '2026-04-25T09:05:00',
    duration_minutes: 25,
    risk_level: 'attention',
  },
];

/**
 * Mock 数据：今日摘要信息
 */
export const mockDailySummaryInput: DailyBehaviorSummaryInput = {
  wake_time: '07:30',
  total_active_minutes: 180,
  bathroom_count: 2,
  longest_bathroom_minutes: 25,
  night_wake_count: 0,
  alerts_count: 1,
  highest_risk: 'attention',
};

/**
 * Mock 数据：老人的基本信息
 */
export const mockElderlyInfo = {
  id: 'elderly-001',
  name: '王奶奶',
  home_id: 'home-001',
  age: 78,
};
