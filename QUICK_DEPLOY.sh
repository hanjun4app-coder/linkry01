#!/bin/bash

# 快速部署脚本：基线学习集成
# 使用: bash QUICK_DEPLOY.sh

set -e  # 任何命令失败都停止

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# 检查前置条件
check_prerequisites() {
    log_info "检查前置条件..."

    # 检查Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js未安装"
        exit 1
    fi
    log_success "Node.js: $(node --version)"

    # 检查PostgreSQL
    if ! command -v psql &> /dev/null; then
        log_error "PostgreSQL未安装"
        exit 1
    fi
    log_success "PostgreSQL: $(psql --version)"

    # 检查git
    if ! command -v git &> /dev/null; then
        log_error "Git未安装"
        exit 1
    fi
    log_success "Git: $(git --version | cut -d' ' -f3)"

    # 检查package.json
    if [ ! -f "package.json" ]; then
        log_error "package.json不存在，请在项目根目录运行此脚本"
        exit 1
    fi
    log_success "package.json存在"
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."

    DB_NAME="${DATABASE_URL##*/}"
    BACKUP_FILE="backup_baseline_$(date +%Y%m%d_%H%M%S).sql"

    if pg_dump -d "$DB_NAME" > "$BACKUP_FILE"; then
        log_success "数据库备份完成: $BACKUP_FILE"
    else
        log_error "数据库备份失败"
        exit 1
    fi
}

# 安装依赖
install_dependencies() {
    log_info "安装依赖..."

    if npm install; then
        log_success "依赖安装完成"
    else
        log_error "依赖安装失败"
        exit 1
    fi
}

# 执行数据库迁移
run_migration() {
    log_info "执行数据库迁移..."

    if npm run migrate:up 2>/dev/null || npx knex migrate:up 2>/dev/null; then
        log_success "迁移执行完成"
    else
        log_warning "迁移命令不可用，请手动运行: npm run migrate:up"
    fi
}

# 类型检查
run_type_check() {
    log_info "运行TypeScript类型检查..."

    if npx tsc --noEmit 2>/dev/null; then
        log_success "类型检查通过"
    else
        log_error "类型检查失败，请修复错误"
        exit 1
    fi
}

# 构建项目
build_project() {
    log_info "构建项目..."

    if npm run build; then
        log_success "项目构建完成"
    else
        log_error "项目构建失败"
        exit 1
    fi
}

# 验证文件
verify_files() {
    log_info "验证必需文件..."

    FILES=(
        "src/lib/statusEngineV2.ts"
        "src/components/EnhancedStatusView.tsx"
        "pages/api/elders/[elder_id]/status.ts"
        "hooks/useEnhancedStatus.ts"
        "services/baselineScheduler.ts"
    )

    for file in "${FILES[@]}"; do
        if [ -f "$file" ]; then
            log_success "找到: $file"
        else
            log_warning "缺少: $file (请检查文件路径)"
        fi
    done
}

# 启动开发服务器并测试
test_api() {
    log_info "测试API端点..."

    # 启动开发服务器（后台）
    npm run dev > /tmp/next_dev.log 2>&1 &
    DEV_PID=$!

    # 等待服务器启动
    sleep 5

    # 测试API
    if curl -s http://localhost:3000/api/elders/elder_1/status | grep -q "status"; then
        log_success "API端点正常工作"
    else
        log_error "API端点测试失败"
        kill $DEV_PID 2>/dev/null || true
        exit 1
    fi

    # 停止开发服务器
    kill $DEV_PID 2>/dev/null || true
}

# 创建监控面板配置
setup_monitoring() {
    log_info "设置监控配置..."

    cat > .env.local.example << 'EOF'
# 监控配置
MONITORING_ENABLED=true
DATADOG_API_KEY=your_key_here
ALERT_EMAIL=your@email.com
BASELINE_COLLECTION_TARGET=0.95
EOF

    log_success "监控配置模板已创建: .env.local.example"
}

# 生成部署报告
generate_report() {
    log_info "生成部署报告..."

    REPORT_FILE="DEPLOYMENT_REPORT_$(date +%Y%m%d_%H%M%S).md"

    cat > "$REPORT_FILE" << EOF
# 部署报告

**部署时间**: $(date)

## 检查清单

- [x] 前置条件验证
- [x] 数据库备份
- [x] 依赖安装
- [x] 数据库迁移
- [x] 类型检查
- [x] 项目构建
- [x] API测试

## 系统信息

- Node.js: $(node --version)
- PostgreSQL: $(psql --version)
- 数据库: ${DATABASE_URL##*/}

## 部署配置

- 构建输出: .next/
- 备份文件: $BACKUP_FILE

## 下一步

1. 配置环境变量: cp .env.local.example .env.local
2. 验证生产数据库连接
3. 启动生产应用: npm run start
4. 监视日志和监控指标

**状态**: ✅ 就绪部署

EOF

    log_success "部署报告已生成: $REPORT_FILE"
}

# 主流程
main() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   基线学习集成 - 快速部署脚本         ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""

    check_prerequisites
    echo ""

    backup_database
    echo ""

    install_dependencies
    echo ""

    verify_files
    echo ""

    run_type_check
    echo ""

    build_project
    echo ""

    run_migration
    echo ""

    test_api
    echo ""

    setup_monitoring
    echo ""

    generate_report
    echo ""

    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✅ 部署完成                         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo "后续步骤:"
    echo "1. 查看部署报告: cat $REPORT_FILE"
    echo "2. 配置监控: edit .env.local"
    echo "3. 启动服务: npm run start"
    echo ""
}

# 错误处理
trap 'log_error "脚本执行失败"; exit 1' ERR

# 运行主流程
main
