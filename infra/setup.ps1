#!/usr/bin/env pwsh
# ============================================================
# setup.ps1 — Script khởi tạo toàn bộ hạ tầng AI Agent
# Chạy: .\infra\setup.ps1
# ============================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Privacy Shield — AI Agent Infrastructure Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# --- Bước 1: Kiểm tra Docker ---
Write-Host "[1/6] Kiểm tra Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "  ✓ $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker chưa được cài đặt. Hãy cài tại: https://www.docker.com/products/docker-desktop" -ForegroundColor Red
    exit 1
}

# --- Bước 2: Tạo file .env ---
Write-Host ""
Write-Host "[2/6] Chuẩn bị file cấu hình (.env)..." -ForegroundColor Yellow
$envFile = Join-Path $PSScriptRoot ".env"
$envExample = Join-Path $PSScriptRoot ".env.example"

if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "  ✓ Đã tạo file .env từ .env.example" -ForegroundColor Green
    Write-Host "  ⚠ Hãy mở infra/.env và điền các thông tin cần thiết!" -ForegroundColor Yellow
    Write-Host "    (Ít nhất cần đổi POSTGRES_PASSWORD và REDIS_PASSWORD)" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ File .env đã tồn tại" -ForegroundColor Green
}

# --- Bước 3: Khởi động Docker services ---
Write-Host ""
Write-Host "[3/6] Khởi động Docker Compose services..." -ForegroundColor Yellow
Write-Host "  (Lần đầu sẽ tải Docker images, có thể mất 3-10 phút)" -ForegroundColor DarkGray

Set-Location $PSScriptRoot
docker compose --env-file .env up -d --remove-orphans

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Lỗi khi khởi động Docker. Kiểm tra lại docker-compose.yml" -ForegroundColor Red
    exit 1
}

Write-Host "  ✓ Docker services đã khởi động" -ForegroundColor Green

# --- Bước 4: Chờ PostgreSQL sẵn sàng ---
Write-Host ""
Write-Host "[4/6] Chờ PostgreSQL sẵn sàng..." -ForegroundColor Yellow
$maxRetries = 15
$retry = 0
do {
    Start-Sleep -Seconds 3
    $retry++
    $result = docker exec privacy_shield_postgres pg_isready -q 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ PostgreSQL sẵn sàng (sau $($retry * 3)s)" -ForegroundColor Green
        break
    }
    Write-Host "  ... đang chờ ($retry/$maxRetries)" -ForegroundColor DarkGray
} while ($retry -lt $maxRetries)

if ($retry -eq $maxRetries) {
    Write-Host "  ✗ PostgreSQL chưa sẵn sàng sau $($maxRetries * 3)s" -ForegroundColor Red
}

# --- Bước 5: Kiểm tra Ollama chạy trên Windows host ---
Write-Host ""
Write-Host "[5/6] Kiểm tra Ollama host và model llama3.2:3b..." -ForegroundColor Yellow
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    ollama list | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Ollama CLI có mặt nhưng service chưa chạy tại localhost:11434" -ForegroundColor Red
        Write-Host "    Hãy mở Ollama rồi chạy lại script." -ForegroundColor Yellow
        exit 1
    }
    ollama pull llama3.2:3b
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Không tải được model llama3.2:3b" -ForegroundColor Red
        exit 1
    }
    Write-Host "  ✓ Ollama host và model đã sẵn sàng" -ForegroundColor Green
} else {
    Write-Host "  ✗ Không tìm thấy Ollama CLI trên Windows host." -ForegroundColor Red
    Write-Host "    Cài Ollama hoặc đổi LiteLLM config sang cloud provider trước khi tiếp tục." -ForegroundColor Yellow
    exit 1
}

# --- Bước 6: Hiển thị URLs ---
Write-Host ""
Write-Host "[6/6] Hoàn thành! Các service đang chạy:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  📊 Langfuse Dashboard (AgentOps): http://localhost:3000" -ForegroundColor Cyan
Write-Host "     → Đăng ký tài khoản lần đầu tại đây" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  🔄 LiteLLM Gateway (Governance):  http://localhost:4000" -ForegroundColor Cyan
Write-Host "     → Giao diện quản lý: http://localhost:4000/ui" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  🗄️  PostgreSQL (Memory & RAG):     localhost:5432" -ForegroundColor Cyan
Write-Host "     → Dùng pgAdmin hoặc DBeaver để xem database" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  ⚡ Redis (Checkpoints):            localhost:6379" -ForegroundColor Cyan
Write-Host ""
Write-Host "  🤖 Ollama (Local LLM):             http://localhost:11434" -ForegroundColor Cyan
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Bước tiếp theo:" -ForegroundColor Green
Write-Host "  1. Mở http://localhost:3000 → Đăng ký tài khoản Langfuse" -ForegroundColor White
Write-Host "  2. Lấy Public/Secret Key từ Langfuse → Điền vào .env" -ForegroundColor White
Write-Host "  3. cd ai-project-agent" -ForegroundColor White
Write-Host "  4. python -m venv .venv && .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  5. pip install -r requirements.txt" -ForegroundColor White
Write-Host "  6. python rag/rag_ingest.py  (nhúng tài liệu vào RAG)" -ForegroundColor White
Write-Host "  7. python graph/supervisor.py  (test Agent)" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
