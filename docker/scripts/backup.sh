#!/bin/bash
# =============================================================================
# Poly-Spinor Nexus 7D - Backup Script
# =============================================================================

set -e

# Configuration
BACKUP_DIR="/backups"
SOURCE_DIR="/app/vault_storage"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="vault_backup_${TIMESTAMP}"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
COMPRESSION=${BACKUP_COMPRESSION:-true}

echo "[$(date)] Starting backup..."

# Create backup directory if not exists
mkdir -p "${BACKUP_DIR}"

# Create backup
if [ "${COMPRESSION}" = "true" ]; then
    tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" -C "${SOURCE_DIR}" .
    echo "[$(date)] Created compressed backup: ${BACKUP_NAME}.tar.gz"
else
    tar -cf "${BACKUP_DIR}/${BACKUP_NAME}.tar" -C "${SOURCE_DIR}" .
    echo "[$(date)] Created backup: ${BACKUP_NAME}.tar"
fi

# Calculate checksum
if [ "${COMPRESSION}" = "true" ]; then
    sha256sum "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" > "${BACKUP_DIR}/${BACKUP_NAME}.sha256"
else
    sha256sum "${BACKUP_DIR}/${BACKUP_NAME}.tar" > "${BACKUP_DIR}/${BACKUP_NAME}.sha256"
fi

echo "[$(date)] Checksum created"

# Cleanup old backups
echo "[$(date)] Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "vault_backup_*.tar*" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name "vault_backup_*.sha256" -mtime +${RETENTION_DAYS} -delete

# List current backups
echo "[$(date)] Current backups:"
ls -lh "${BACKUP_DIR}"/vault_backup_* 2>/dev/null || echo "No backups found"

echo "[$(date)] Backup completed successfully"
