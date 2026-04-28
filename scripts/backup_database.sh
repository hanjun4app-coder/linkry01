#!/bin/bash

# 数据库备份脚本
# 用途：备份 PostgreSQL 数据库，支持全量备份和选择性备份

set -e

# ==================== 配置 ====================

# 数据库连接信息
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-elderly_admin}
POSTGRES_DB=${POSTGRES_DB:-elderly_care}

# 备份目录
BACKUP_DIR=${BACKUP_DIR:-./backups}
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)

# 备份类型
BACKUP_TYPE=${BACKUP_TYPE:-full}  # full, tables, schemas, data_only

# 日志
LOG_FILE="${BACKUP_DIR}/backup_${BACKUP_DATE}.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ==================== 函数 ====================

# 日志函数
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"
}

# 创建备份目录
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log "Created backup directory: $BACKUP_DIR"
    fi
}

# 检查数据库连接
check_db_connection() {
    log "Checking database connection..."
    if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" > /dev/null 2>&1; then
        log_success "Database connection successful"
        return 0
    else
        log_error "Cannot connect to database"
        return 1
    fi
}

# 全量备份（格式：custom format 便于恢复）
backup_full() {
    local backup_file="${BACKUP_DIR}/${POSTGRES_DB}_full_${BACKUP_DATE}.dump"
    log "Starting full database backup..."

    if PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -v > "$backup_file" 2>> "$LOG_FILE"; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_success "Full backup completed: $backup_file ($size)"
        echo "$backup_file"
    else
        log_error "Full backup failed"
        return 1
    fi
}

# 模式备份（仅数据库结构）
backup_schemas() {
    local backup_file="${BACKUP_DIR}/${POSTGRES_DB}_schemas_${BACKUP_DATE}.sql"
    log "Starting schema-only backup..."

    if PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -s -v > "$backup_file" 2>> "$LOG_FILE"; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_success "Schema backup completed: $backup_file ($size)"
        echo "$backup_file"
    else
        log_error "Schema backup failed"
        return 1
    fi
}

# 数据备份（仅数据，不含结构）
backup_data_only() {
    local backup_file="${BACKUP_DIR}/${POSTGRES_DB}_data_${BACKUP_DATE}.sql"
    log "Starting data-only backup..."

    if PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -a -v > "$backup_file" 2>> "$LOG_FILE"; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_success "Data backup completed: $backup_file ($size)"
        echo "$backup_file"
    else
        log_error "Data backup failed"
        return 1
    fi
}

# 选择性表备份
backup_selected_tables() {
    local tables="families,elders,devices,events,daily_summaries,alerts,alert_feedback,patterns"
    local backup_file="${BACKUP_DIR}/${POSTGRES_DB}_tables_${BACKUP_DATE}.dump"
    log "Starting selected tables backup..."

    # 构建 table 参数
    local table_args=""
    IFS=',' read -ra TABLE_ARRAY <<< "$tables"
    for table in "${TABLE_ARRAY[@]}"; do
        table_args="$table_args -t $table"
    done

    if PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc $table_args -v > "$backup_file" 2>> "$LOG_FILE"; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_success "Tables backup completed: $backup_file ($size)"
        echo "$backup_file"
    else
        log_error "Tables backup failed"
        return 1
    fi
}

# 备份统计信息
backup_statistics() {
    local backup_file="${BACKUP_DIR}/${POSTGRES_DB}_stats_${BACKUP_DATE}.txt"
    log "Collecting database statistics..."

    cat > "$backup_file" << EOF
Database Backup Statistics
Generated: $(date '+%Y-%m-%d %H:%M:%S')

=== Database Info ===
Host: $POSTGRES_HOST
Port: $POSTGRES_PORT
Database: $POSTGRES_DB
User: $POSTGRES_USER

=== Table Statistics ===
EOF

    PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" >> "$backup_file" 2>&1 << 'EOSQL'
\x
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
EOSQL

    log_success "Statistics saved: $backup_file"
}

# 压缩备份文件
compress_backup() {
    local backup_file=$1
    if [ -f "$backup_file" ] && [[ "$backup_file" == *.sql ]]; then
        log "Compressing backup file..."
        if gzip "$backup_file"; then
            log_success "Backup compressed: ${backup_file}.gz"
            echo "${backup_file}.gz"
        else
            log_warning "Compression failed, keeping original file"
            echo "$backup_file"
        fi
    else
        echo "$backup_file"
    fi
}

# 清理旧备份（保留最近 7 天）
cleanup_old_backups() {
    log "Cleaning up old backups (keeping last 7 days)..."
    local cutoff_date=$(date -d '7 days ago' +%s 2>/dev/null || date -v-7d +%s)

    find "$BACKUP_DIR" -type f \( -name "*.dump" -o -name "*.sql.gz" -o -name "*.sql" \) -print0 | while IFS= read -r -d '' file; do
        local file_date=$(stat -f%m "$file" 2>/dev/null || stat -c%Y "$file")
        if [ "$file_date" -lt "$cutoff_date" ]; then
            rm -f "$file"
            log "Removed old backup: $file"
        fi
    done
    log_success "Cleanup completed"
}

# 验证备份完整性
verify_backup() {
    local backup_file=$1
    log "Verifying backup file..."

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi

    local size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file")
    if [ "$size" -gt 0 ]; then
        log_success "Backup verified (size: $(du -h "$backup_file" | cut -f1))"
        return 0
    else
        log_error "Backup file is empty"
        return 1
    fi
}

# ==================== 主程序 ====================

main() {
    echo -e "${YELLOW}=====================================${NC}"
    echo -e "${YELLOW}PostgreSQL Database Backup Script${NC}"
    echo -e "${YELLOW}=====================================${NC}"

    create_backup_dir

    # 检查连接
    if ! check_db_connection; then
        log_error "Backup aborted: database not accessible"
        exit 1
    fi

    local backup_file=""

    # 根据备份类型执行
    case $BACKUP_TYPE in
        full)
            backup_file=$(backup_full)
            ;;
        schemas)
            backup_file=$(backup_schemas)
            ;;
        data_only)
            backup_file=$(backup_data_only)
            ;;
        tables)
            backup_file=$(backup_selected_tables)
            ;;
        *)
            log_error "Unknown backup type: $BACKUP_TYPE"
            exit 1
            ;;
    esac

    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        log_error "Backup failed or no file generated"
        exit 1
    fi

    # 收集统计信息
    backup_statistics

    # 验证备份
    if verify_backup "$backup_file"; then
        # 压缩（如果是 SQL 文件）
        backup_file=$(compress_backup "$backup_file")

        # 清理旧备份
        cleanup_old_backups

        log_success "Backup completed successfully!"
        echo -e "${GREEN}Backup file: $backup_file${NC}"
        exit 0
    else
        log_error "Backup verification failed"
        exit 1
    fi
}

# ==================== 帮助信息 ====================

show_help() {
    cat << EOF
Usage: bash backup_database.sh [OPTIONS]

Options:
    -t, --type TYPE           Backup type: full, schemas, data_only, tables
                             Default: full
    -h, --host HOST          PostgreSQL host (default: localhost)
    -p, --port PORT          PostgreSQL port (default: 5432)
    -u, --user USER          PostgreSQL user (default: elderly_admin)
    -d, --database DB        Database name (default: elderly_care)
    -b, --backup-dir DIR     Backup directory (default: ./backups)
    --help                   Show this help message

Examples:
    # Full backup
    bash backup_database.sh

    # Schema-only backup
    bash backup_database.sh -t schemas

    # Data-only backup
    bash backup_database.sh -t data_only

    # Custom location
    bash backup_database.sh -b /var/backups/elderly_care

Environment Variables:
    POSTGRES_HOST            PostgreSQL host
    POSTGRES_PORT            PostgreSQL port
    POSTGRES_USER            PostgreSQL user
    POSTGRES_PASSWORD        PostgreSQL password (required)
    POSTGRES_DB              Database name
    BACKUP_DIR              Backup directory
    BACKUP_TYPE             Backup type

EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            BACKUP_TYPE="$2"
            shift 2
            ;;
        -h|--host)
            POSTGRES_HOST="$2"
            shift 2
            ;;
        -p|--port)
            POSTGRES_PORT="$2"
            shift 2
            ;;
        -u|--user)
            POSTGRES_USER="$2"
            shift 2
            ;;
        -d|--database)
            POSTGRES_DB="$2"
            shift 2
            ;;
        -b|--backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

main "$@"
