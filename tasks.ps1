param(
    [Parameter(Position = 0)]
    [string]$Task = "help",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Run-Python {
    param([string[]]$ArgsList)
    & python @ArgsList
}

function Show-Help {
    Write-Host "PoE Filter Toolkit - atalhos locais"
    Write-Host ""
    Write-Host "Uso:"
    Write-Host "  .\tasks.ps1 test"
    Write-Host "  .\tasks.ps1 character [slug] [budget]"
    Write-Host "  .\tasks.ps1 filter [slug]"
    Write-Host "  .\tasks.ps1 sync-pob [slug] [pob_xml_path]"
    Write-Host "  .\tasks.ps1 clean-local"
    Write-Host ""
    Write-Host "Defaults:"
    Write-Host "  slug   = aron_shockwave_cyclone_slayer"
    Write-Host "  budget = 1000c"
}

switch ($Task.ToLowerInvariant()) {
    "help" {
        Show-Help
    }
    "test" {
        Run-Python @("-m", "unittest", "discover", "-s", "poe_market_filter_toolkit\tests")
    }
    "character" {
        $Slug = if ($Rest.Count -ge 1) { $Rest[0] } else { "aron_shockwave_cyclone_slayer" }
        $Budget = if ($Rest.Count -ge 2) { $Rest[1] } else { "1000c" }
        Run-Python @("poe_market_filter_toolkit\scripts\run_character.py", "--character", $Slug, "--budget", $Budget, "--open")
    }
    "filter" {
        $Slug = if ($Rest.Count -ge 1) { $Rest[0] } else { "aron_shockwave_cyclone_slayer" }
        Run-Python @("poe_market_filter_toolkit\scripts\review_filter_strategy.py", "--character", $Slug)
        Run-Python @("poe_market_filter_toolkit\scripts\filter_audit.py")
        Run-Python @("poe_market_filter_toolkit\scripts\suggest_filter_tiers.py")
    }
    "sync-pob" {
        if ($Rest.Count -lt 2) {
            throw "Uso: .\tasks.ps1 sync-pob <character_slug> <pob_xml_path>"
        }
        Run-Python @("poe_market_filter_toolkit\scripts\sync_pob.py", "--character", $Rest[0], "--source", $Rest[1])
    }
    "clean-local" {
        $repo = (Resolve-Path ".").Path
        Get-ChildItem -Path "poe_market_filter_toolkit" -Recurse -Directory -Filter "__pycache__" | ForEach-Object {
            $resolved = (Resolve-Path -LiteralPath $_.FullName).Path
            if (-not $resolved.StartsWith($repo)) { throw "Path outside repo: $resolved" }
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
        Get-ChildItem -Path "poe_market_filter_toolkit\data\generated" -Recurse -Filter "*.log" -ErrorAction SilentlyContinue | ForEach-Object {
            $resolved = (Resolve-Path -LiteralPath $_.FullName).Path
            if (-not $resolved.StartsWith($repo)) { throw "Path outside repo: $resolved" }
            Remove-Item -LiteralPath $resolved -Force
        }
        Write-Host "Limpeza local concluida."
    }
    default {
        Show-Help
        throw "Task desconhecida: $Task"
    }
}
