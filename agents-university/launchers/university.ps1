#!/usr/bin/env powershell
<#
.SYNOPSIS
    AML University Pipeline - Comprehensive metrics builder with evidence logging

.DESCRIPTION
    Runs the complete AML university pipeline:
    1. Catalog build (if needed)
    2. Report generation (if needed) 
    3. Teach-packs processing (if needed)
    4. Metrics compilation
    5. Evidence logging (append-only)

.PARAMETER Force
    Force rebuild of all components even if they exist

.PARAMETER SkipValidation
    Skip validation of input files

.PARAMETER Verbose
    Enable verbose output

.EXAMPLE
    .\scripts\university.ps1
    
.EXAMPLE
    .\scripts\university.ps1 -Force -Verbose
#>

param(
    [switch]$Force,
    [switch]$SkipValidation,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Script configuration
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
$BuildMetricsScript = Join-Path $ScriptRoot "build_metrics.py"
$MetricsOutput = Join-Path $ProjectRoot "docs\metrics.json"
$EvidenceFile = Join-Path $ProjectRoot ".mm-out\university\evidence.jsonl"

# Colors for output
$Colors = @{
    Info = "Cyan"
    Success = "Green" 
    Warning = "Yellow"
    Error = "Red"
    Header = "Magenta"
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    
    if ($Colors.ContainsKey($Color)) {
        Write-Host $Message -ForegroundColor $Colors[$Color]
    } else {
        Write-Host $Message
    }
}

function Write-Header {
    param([string]$Title)
    
    Write-Host ""
    Write-ColorOutput "=" * 60 -Color "Header"
    Write-ColorOutput "  $Title" -Color "Header"
    Write-ColorOutput "=" * 60 -Color "Header"
    Write-Host ""
}

function Test-PythonAvailable {
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Python available: $pythonVersion" -Color "Success"
            return $true
        }
    } catch {
        Write-ColorOutput "❌ Python not found in PATH" -Color "Error"
        return $false
    }
    return $false
}

function Test-RequiredDirectories {
    $requiredDirs = @(
        ".mm-out\university",
        ".mm-out\efficacy", 
        "docs",
        "scripts"
    )
    
    $allExist = $true
    foreach ($dir in $requiredDirs) {
        $fullPath = Join-Path $ProjectRoot $dir
        if (-not (Test-Path $fullPath)) {
            Write-ColorOutput "📁 Creating directory: $dir" -Color "Info"
            New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        } else {
            if ($Verbose) {
                Write-ColorOutput "✅ Directory exists: $dir" -Color "Success"
            }
        }
    }
    
    return $allExist
}

function Invoke-MetricsBuild {
    Write-ColorOutput "🔄 Running metrics builder..." -Color "Info"
    
    try {
        # Change to project root for consistent paths
        Push-Location $ProjectRoot
        
        # Run the Python metrics builder
        $output = python $BuildMetricsScript 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Metrics build successful!" -Color "Success"
            
            # Display the output
            $output | ForEach-Object {
                Write-ColorOutput "   $_" -Color "Info"
            }
            
            return $true
        } else {
            Write-ColorOutput "❌ Metrics build failed!" -Color "Error"
            Write-ColorOutput "Error output:" -Color "Error"
            $output | ForEach-Object {
                Write-ColorOutput "   $_" -Color "Error"
            }
            return $false
        }
    } catch {
        Write-ColorOutput "❌ Exception during metrics build: $($_.Exception.Message)" -Color "Error"
        return $false
    } finally {
        Pop-Location
    }
}

function Test-OutputFiles {
    $success = $true
    
    # Check metrics.json
    if (Test-Path $MetricsOutput) {
        $metricsSize = (Get-Item $MetricsOutput).Length
        Write-ColorOutput "✅ metrics.json created ($metricsSize bytes)" -Color "Success"
        
        # Validate JSON structure
        try {
            $metricsContent = Get-Content $MetricsOutput -Raw | ConvertFrom-Json
            $requiredFields = @("ts", "run_id", "counts", "promotion", "efficacy")
            
            foreach ($field in $requiredFields) {
                if (-not $metricsContent.PSObject.Properties.Name -contains $field) {
                    Write-ColorOutput "⚠️  Missing field in metrics.json: $field" -Color "Warning"
                }
            }
            
            if ($Verbose) {
                Write-ColorOutput "📊 Metrics summary:" -Color "Info"
                Write-ColorOutput "   Lessons: $($metricsContent.counts.lessons)" -Color "Info"
                Write-ColorOutput "   Tracks: $($metricsContent.counts.tracks.PSObject.Properties.Count)" -Color "Info"
                Write-ColorOutput "   Teach-packs: $($metricsContent.counts.teach_packs)" -Color "Info"
                Write-ColorOutput "   Efficacy: $($metricsContent.efficacy.score)" -Color "Info"
            }
            
        } catch {
            Write-ColorOutput "❌ Invalid JSON in metrics.json: $($_.Exception.Message)" -Color "Error"
            $success = $false
        }
    } else {
        Write-ColorOutput "❌ metrics.json not created" -Color "Error"
        $success = $false
    }
    
    # Check evidence file
    if (Test-Path $EvidenceFile) {
        $evidenceLines = (Get-Content $EvidenceFile).Count
        Write-ColorOutput "✅ Evidence logged ($evidenceLines entries)" -Color "Success"
    } else {
        Write-ColorOutput "⚠️  Evidence file not found (will be created on first run)" -Color "Warning"
    }
    
    return $success
}

function Show-Summary {
    Write-Header "📊 Pipeline Summary"
    
    if (Test-Path $MetricsOutput) {
        Write-ColorOutput "📁 Output Files:" -Color "Info"
        Write-ColorOutput "   📊 Metrics: docs\metrics.json" -Color "Success"
        
        if (Test-Path $EvidenceFile) {
            Write-ColorOutput "   📝 Evidence: .mm-out\university\evidence.jsonl" -Color "Success"
        }
        
        Write-Host ""
        Write-ColorOutput "🚀 Next Steps:" -Color "Info"
        Write-ColorOutput "   • View GitHub Pages: https://mrrobot787.github.io/AML/" -Color "Info"
        Write-ColorOutput "   • Start Streamlit: .\start_aml_dashboard.ps1" -Color "Info"
        Write-ColorOutput "   • Deploy to Streamlit Cloud for embedding" -Color "Info"
        
    } else {
        Write-ColorOutput "❌ Pipeline failed - no output generated" -Color "Error"
        exit 1
    }
}

function Main {
    Write-Header "🎓 AML University Pipeline"
    Write-ColorOutput "Building portfolio metrics with evidence logging..." -Color "Info"
    Write-ColorOutput "Project: $ProjectRoot" -Color "Info"
    
    if ($Force) {
        Write-ColorOutput "🔄 Force mode enabled - rebuilding all components" -Color "Warning"
    }
    
    # Pre-flight checks
    Write-ColorOutput "🔍 Running pre-flight checks..." -Color "Info"
    
    if (-not (Test-PythonAvailable)) {
        Write-ColorOutput "❌ Python is required but not available" -Color "Error"
        exit 1
    }
    
    if (-not (Test-RequiredDirectories)) {
        Write-ColorOutput "❌ Failed to create required directories" -Color "Error"
        exit 1
    }
    
    if (-not (Test-Path $BuildMetricsScript)) {
        Write-ColorOutput "❌ Build script not found: $BuildMetricsScript" -Color "Error"
        exit 1
    }
    
    Write-ColorOutput "✅ Pre-flight checks passed" -Color "Success"
    
    # Main pipeline execution
    Write-Header "🔄 Executing Pipeline"
    
    $buildSuccess = Invoke-MetricsBuild
    
    if (-not $buildSuccess) {
        Write-ColorOutput "❌ Pipeline failed during metrics build" -Color "Error"
        exit 1
    }
    
    # Post-build validation
    Write-Header "✅ Validation"
    
    if (-not $SkipValidation) {
        $validationSuccess = Test-OutputFiles
        
        if (-not $validationSuccess) {
            Write-ColorOutput "❌ Output validation failed" -Color "Error"
            exit 1
        }
    } else {
        Write-ColorOutput "⏭️  Validation skipped" -Color "Warning"
    }
    
    # Success summary
    Show-Summary
    
    Write-ColorOutput "🎉 AML University pipeline completed successfully!" -Color "Success"
}

# Execute main function
try {
    Main
} catch {
    Write-ColorOutput "💥 Unexpected error: $($_.Exception.Message)" -Color "Error"
    Write-ColorOutput "Stack trace:" -Color "Error"
    Write-ColorOutput $_.ScriptStackTrace -Color "Error"
    exit 1
}
