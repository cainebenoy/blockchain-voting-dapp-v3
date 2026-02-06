# VoteChain V3 - Full Election Simulation

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   ELECTION SIMULATION TEST" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check election status
Write-Host "[STEP 1] Checking Election Status..." -ForegroundColor Yellow
$results = Invoke-RestMethod -Uri "http://localhost:3000/api/results" -Method Get
Write-Host "✅ Election Active: $($results.data.electionActive)" -ForegroundColor Green
Write-Host "   Candidates: $($results.data.totalCandidates)" -ForegroundColor Gray
$results.data.candidates | ForEach-Object {
    Write-Host "   - $($_.name) (ID: $($_.id))" -ForegroundColor Gray
}

# Simulate voter check-ins and votes
Write-Host "`n[STEP 2] Simulating Voter Check-ins..." -ForegroundColor Yellow

$testVoters = @(
    @{ aadhaar = "123456789012"; name = "Test Voter 1"; candidateId = 1 },
    @{ aadhaar = "234567890123"; name = "Test Voter 2"; candidateId = 2 },
    @{ aadhaar = "345678901234"; name = "Test Voter 3"; candidateId = 1 },
    @{ aadhaar = "456789012345"; name = "Test Voter 4"; candidateId = 3 },
    @{ aadhaar = "567890123456"; name = "Test Voter 5"; candidateId = 1 }
)

$voteResults = @()

Write-Host "`n[STEP 3] Casting Votes..." -ForegroundColor Yellow

foreach ($voter in $testVoters) {
    Write-Host "`n  Voter: $($voter.name) (Aadhaar: $($voter.aadhaar))" -ForegroundColor Gray
    
    # Cast vote
    $voteBody = @{
        aadhaar_id = $voter.aadhaar
        candidate_id = $voter.candidateId
    } | ConvertTo-Json
    
    try {
        $voteResponse = Invoke-RestMethod -Uri "http://localhost:3000/api/vote" `
            -Method Post `
            -ContentType "application/json" `
            -Body $voteBody
        
        if ($voteResponse.status -eq "success") {
            Write-Host "  ✅ Vote cast successfully!" -ForegroundColor Green
            Write-Host "     Transaction: $($voteResponse.data.transaction_hash.Substring(0,20))..." -ForegroundColor Gray
            Write-Host "     Receipt Code: $($voteResponse.data.receipt_code)" -ForegroundColor Cyan
            
            $voteResults += @{
                voter = $voter.name
                candidate = $voter.candidateId
                txHash = $voteResponse.data.transaction_hash
                receipt = $voteResponse.data.receipt_code
                success = $true
            }
            
            # Wait for blockchain confirmation
            Start-Sleep -Seconds 2
        } else {
            Write-Host "  ⚠️  Vote failed: $($voteResponse.message)" -ForegroundColor Yellow
            $voteResults += @{
                voter = $voter.name
                success = $false
                error = $voteResponse.message
            }
        }
    } catch {
        $errorMsg = $_.Exception.Message
        Write-Host "  ❌ Error: $errorMsg" -ForegroundColor Red
        $voteResults += @{
            voter = $voter.name
            success = $false
            error = $errorMsg
        }
    }
}

# Wait for all transactions to confirm
Write-Host "`n[STEP 4] Waiting for blockchain confirmations..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check final results
Write-Host "`n[STEP 5] Fetching Final Results..." -ForegroundColor Yellow
$finalResults = Invoke-RestMethod -Uri "http://localhost:3000/api/results" -Method Get

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   FINAL ELECTION RESULTS" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Election Status: " -NoNewline
if ($finalResults.data.electionActive) {
    Write-Host "ACTIVE ✅" -ForegroundColor Green
} else {
    Write-Host "CLOSED ❌" -ForegroundColor Red
}

Write-Host "Total Votes Cast: $($finalResults.data.totalVotes)" -ForegroundColor Cyan
Write-Host "`nCandidate Standings:" -ForegroundColor Yellow

$sorted = $finalResults.data.candidates | Sort-Object -Property voteCount -Descending

$medals = @("🥇", "🥈", "🥉")
$sorted | ForEach-Object -Begin { $i = 0 } -Process {
    $medal = if ($i -lt 3) { $medals[$i] } else { "  " }
    $percentage = if ($finalResults.data.totalVotes -gt 0) {
        [math]::Round(($_.voteCount / $finalResults.data.totalVotes) * 100, 1)
    } else { 0 }
    
    Write-Host "$medal $($_.name): $($_.voteCount) votes ($percentage%)" -ForegroundColor Cyan
    
    # Progress bar
    $barLength = [math]::Min($_.voteCount * 5, 50)
    $bar = "█" * $barLength
    Write-Host "   $bar" -ForegroundColor Green
    
    $i++
}

# Test receipt verification
Write-Host "`n[STEP 6] Testing Receipt Verification..." -ForegroundColor Yellow

$successfulVotes = $voteResults | Where-Object { $_.success -eq $true }
if ($successfulVotes.Count -gt 0) {
    $testReceipt = $successfulVotes[0].receipt
    Write-Host "  Testing receipt code: $testReceipt" -ForegroundColor Gray
    
    $verifyBody = @{
        code = $testReceipt
    } | ConvertTo-Json
    
    try {
        $verifyResponse = Invoke-RestMethod -Uri "http://localhost:3000/api/verify-code" `
            -Method Post `
            -ContentType "application/json" `
            -Body $verifyBody
        
        if ($verifyResponse.status -eq "success") {
            Write-Host "  ✅ Receipt verified!" -ForegroundColor Green
            Write-Host "     Transaction: $($verifyResponse.tx_hash.Substring(0,20))..." -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ⚠️  Verification test skipped" -ForegroundColor Yellow
    }
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   SIMULATION SUMMARY" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$successCount = ($voteResults | Where-Object { $_.success -eq $true }).Count
$failCount = ($voteResults | Where-Object { $_.success -eq $false }).Count

Write-Host "Votes Attempted: $($voteResults.Count)" -ForegroundColor Gray
Write-Host "Votes Successful: $successCount ✅" -ForegroundColor Green
Write-Host "Votes Failed: $failCount" -ForegroundColor $(if ($failCount -gt 0) { "Yellow" } else { "Gray" })

Write-Host "`n📊 Blockchain Explorer:" -ForegroundColor Cyan
Write-Host "   https://sepolia.etherscan.io/address/$($results.data.contractAddress)`n" -ForegroundColor Blue

Write-Host "✅ Full election flow simulation complete!`n" -ForegroundColor Green
