# LiangHua Platform - Port Cleanup Script
# Kill processes occupying port 8001 (backend) and 3000 (frontend)
# Also cleans up uvicorn --reload child processes (multiprocessing fork workers)

$ports = @(8001, 3000)
$anyKilled = $false

# Helper: get PIDs listening on a port using Get-NetTCPConnection (native PS cmdlet)
function Get-PortPids($port) {
    $procIds = @()
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        foreach ($c in $conns) {
            if ($c.OwningProcess -and $procIds -notcontains $c.OwningProcess) {
                $procIds += $c.OwningProcess
            }
        }
    } catch {}
    return $procIds
}

# Step 1: Kill processes directly listening on target ports
foreach ($p in $ports) {
    $procIds = Get-PortPids $p
    if ($procIds.Count -gt 0) {
        foreach ($procId in $procIds) {
            try {
                Stop-Process -Id $procId -Force -ErrorAction Stop
                Write-Host "  [OK] Port $p - PID $procId terminated"
                $anyKilled = $true
            } catch {
                Write-Host "  [--] Port $p - PID $procId is ghost (process gone, socket lingering)"
            }
        }
    } else {
        Write-Host "  [OK] Port $p is free"
    }
}

# Step 2: Kill orphan uvicorn/multiprocessing python workers
# (these hold socket handles even when parent is dead)
$orphans = Get-WmiObject Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -like "*uvicorn*" -or
        $_.CommandLine -like "*multiprocessing-fork*" -or
        $_.CommandLine -like "*spawn_main*" -or
        $_.CommandLine -like "*main:app*"
    )
}
if ($orphans) {
    foreach ($orphan in $orphans) {
        try {
            Stop-Process -Id $orphan.ProcessId -Force -ErrorAction Stop
            Write-Host "  [OK] Orphan worker PID $($orphan.ProcessId) terminated"
            $anyKilled = $true
        } catch {
            Write-Host "  [--] Orphan PID $($orphan.ProcessId) already gone"
        }
    }
}

# Step 3: Wait and verify
if ($anyKilled) {
    Write-Host "Waiting for ports to release..."
    Start-Sleep -Seconds 3
}

# Final check
$stillOccupied = @()
foreach ($p in $ports) {
    $procIds = Get-PortPids $p
    if ($procIds.Count -gt 0) {
        $stillOccupied += $p
    }
}
if ($stillOccupied.Count -gt 0) {
    Write-Host "  [WARN] Ports still occupied: $($stillOccupied -join ', ')"
    Write-Host "  [WARN] Try logging out and back in if ghost sockets persist"
} else {
    Write-Host "  [OK] All ports cleared"
}
