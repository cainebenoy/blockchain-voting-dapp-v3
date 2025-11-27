# Test Vote Submission Script
# Make sure backend server is running on port 3000

Write-Host "🗳️  VoteChain - Test Vote Submission" -ForegroundColor Cyan
Write-Host ""

# Test voter (make sure this exists in your Supabase)
$testVoter = @{
    aadhaar_id = "123456789012"
    candidate_id = 1  # Change to match your candidate ID
}

Write-Host "📝 Submitting vote for voter: $($testVoter.aadhaar_id)" -ForegroundColor Yellow
Write-Host "   Candidate ID: $($testVoter.candidate_id)" -ForegroundColor Yellow
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3000/api/vote" -Method Post -ContentType "application/json" -Body ($testVoter | ConvertTo-Json)
    
    Write-Host "✅ SUCCESS!" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor White
    
} catch {
    Write-Host "❌ ERROR!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "💡 Next: Check admin dashboard and public results page to see vote count update" -ForegroundColor Cyan
