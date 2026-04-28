#!/bin/bash

# 测试脚本：测试养老 AI 系统云端 API

set -e

# 配置
API_URL=${API_URL:-"http://localhost:8000"}
API_KEY=${API_KEY:-"your_api_key_change_in_production"}
ELDER_ID="elder_001"
FAMILY_ID="family_001"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}养老 AI 系统云端 API 测试${NC}"
echo -e "${YELLOW}========================================${NC}\n"

# 1. 健康检查
echo -e "${YELLOW}[1/8] 健康检查...${NC}"
HEALTH=$(curl -s "${API_URL}/health")
if echo $HEALTH | grep -q "healthy"; then
    echo -e "${GREEN}✓ API 正常运行${NC}\n"
else
    echo -e "${RED}✗ API 不可用${NC}"
    exit 1
fi

# 2. 创建单个事件
echo -e "${YELLOW}[2/8] 创建单个事件...${NC}"
curl -s -X POST "${API_URL}/api/events" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d @- << EOF | jq .
{
  "elder_id": "${ELDER_ID}",
  "family_id": "${FAMILY_ID}",
  "device_id": "aqara_fp2_bedroom",
  "device_type": "aqara_fp2",
  "event_type": "presence",
  "event_value": {
    "detected": true,
    "distance": 2.5
  },
  "room": "bedroom",
  "confidence": 0.95
}
EOF
echo -e "\n"

# 3. 批量创建事件
echo -e "${YELLOW}[3/8] 批量创建事件...${NC}"
curl -s -X POST "${API_URL}/api/events/bulk" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d @- << EOF | jq .
{
  "batch_id": "batch_test_001",
  "events": [
    {
      "elder_id": "${ELDER_ID}",
      "family_id": "${FAMILY_ID}",
      "device_id": "aqara_fp2_living_room",
      "device_type": "aqara_fp2",
      "event_type": "motion",
      "event_value": {"detected": true},
      "room": "living_room",
      "confidence": 0.9
    },
    {
      "elder_id": "${ELDER_ID}",
      "family_id": "${FAMILY_ID}",
      "device_id": "bathroom_door",
      "device_type": "door_sensor",
      "event_type": "door",
      "event_value": {"opened": true},
      "room": "bathroom",
      "confidence": 1.0
    }
  ]
}
EOF
echo -e "\n"

# 4. 获取最近事件
echo -e "${YELLOW}[4/8] 获取最近 24 小时的事件...${NC}"
curl -s -X GET "${API_URL}/api/events/${ELDER_ID}?family_id=${FAMILY_ID}&hours=24" \
  -H "x-api-key: ${API_KEY}" | jq .
echo -e "\n"

# 5. 按房间获取事件
echo -e "${YELLOW}[5/8] 获取卧室事件...${NC}"
curl -s -X GET "${API_URL}/api/events/${ELDER_ID}/by_room?family_id=${FAMILY_ID}&room=bedroom" \
  -H "x-api-key: ${API_KEY}" | jq .
echo -e "\n"

# 6. 检查规则并生成告警
echo -e "${YELLOW}[6/8] 检查所有规则...${NC}"
curl -s -X POST "${API_URL}/api/events/${ELDER_ID}/check-rules?family_id=${FAMILY_ID}" \
  -H "x-api-key: ${API_KEY}" | jq .
echo -e "\n"

# 7. 创建行为模式
echo -e "${YELLOW}[7/8] 创建行为模式...${NC}"
curl -s -X POST "${API_URL}/api/patterns" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d @- << EOF | jq .
{
  "elder_id": "${ELDER_ID}",
  "family_id": "${FAMILY_ID}",
  "pattern_type": "activity",
  "average_daily_activity_minutes": 180,
  "average_wake_time": "07:00",
  "average_sleep_time": "22:00",
  "average_bathroom_count": 4,
  "average_bathroom_duration_minutes": 15,
  "usual_active_rooms": ["living_room", "kitchen", "bedroom"],
  "days_collected": 7
}
EOF
echo -e "\n"

# 8. 查询告警
echo -e "${YELLOW}[8/8] 查询告警...${NC}"
curl -s -X GET "${API_URL}/api/alerts?family_id=${FAMILY_ID}&days=7&limit=10" \
  -H "x-api-key: ${API_KEY}" | jq .
echo -e "\n"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ 所有测试完成！${NC}"
echo -e "${GREEN}========================================${NC}"
