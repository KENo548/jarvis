# Disk Encryption Guide

JARVIS handles sensitive data (API keys, agent memory, code). Encrypt disks containing this data.

## Linux — LUKS

```bash
# Encrypt a partition (WARNING: destroys existing data)
sudo cryptsetup luksFormat /dev/sdX1
sudo cryptsetup open /dev/sdX1 jarvis-encrypted
sudo mkfs.ext4 /dev/mapper/jarvis-encrypted
sudo mount /dev/mapper/jarvis-encrypted /mnt/jarvis-data

# Auto-mount on boot: add to /etc/crypttab and /etc/fstab
```

## macOS — FileVault

```bash
# Enable FileVault via System Settings > Privacy & Security > FileVault
# Or via command line:
sudo fdesetup enable
```

## Windows — BitLocker

```powershell
# Enable BitLocker on a drive
Enable-BitLocker -MountPoint "D:" -EncryptionMethod XtsAes256 -UsedSpaceOnly -RecoveryPasswordProtector
# Save the recovery password securely (print it or store in keyring)
```

## Docker Volumes

For Docker-hosted services (Chroma, SQLite, Neo4j), encrypt the host directory:

```bash
# Linux: use LUKS on the volume mount point
# macOS: FileVault covers the entire disk
# Windows: BitLocker on the drive containing Docker data
```

## What to Encrypt

| Data | Location | Priority |
|------|----------|----------|
| SQLite databases | `memory/sqlite/` | HIGH — contains task history, agent state |
| Chroma vector DB | `memory/chroma/` | HIGH — contains indexed documents |
| Obsidian vault | `memory/obsidian-vault/` | MEDIUM — contains plans and notes |
| Audit logs | `logs/` | MEDIUM — contains action history |
| Docker volumes | `/var/lib/docker/` | HIGH — contains all container data |
