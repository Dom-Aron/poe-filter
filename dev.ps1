param(
    [Parameter(Position = 0)]
    [string]$Task = "help",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Host "== $Text =="
}

function Show-Help {
    Write-Host "PoE Filter Toolkit - atalhos de desenvolvimento"
    Write-Host ""
    Write-Host "Uso:"
    Write-Host "  .\dev.ps1 check                         Testes, compileall e git status"
    Write-Host "  .\dev.ps1 test                          Executa a suite de testes"
    Write-Host "  .\dev.ps1 compile                       Verifica sintaxe Python via compileall"
    Write-Host "  .\dev.ps1 validate [character_slug]      Valida arquivos de um personagem"
    Write-Host "  .\dev.ps1 status                        Mostra status e commits recentes"
    Write-Host "  .\dev.ps1 changed                       Mostra resumo dos diffs"
    Write-Host "  .\dev.ps1 artifacts                     Lista artefatos ignorados pelo git"
    Write-Host "  .\dev.ps1 clean                         Limpa caches locais seguros"
    Write-Host ""
    Write-Host "Atalhos de uso do projeto ficam em .\tasks.ps1."
}

switch ($Task.ToLowerInvariant()) {
    "help" {
        Show-Help
    }
    "test" {
        Write-Section "tests"
        & python -m unittest discover -s "poe_market_filter_toolkit\tests"
    }
    "compile" {
        Write-Section "compileall"
        & python -m compileall "poe_market_filter_toolkit\core" "poe_market_filter_toolkit\scripts"
    }
    "validate" {
        $Character = if ($Args.Count -ge 1) { $Args[0] } else { "aron_shockwave_cyclone_slayer" }
        Write-Section "validate character: $Character"
        & python "poe_market_filter_toolkit\scripts\validate_character.py" --character $Character
    }
    "check" {
        Write-Section "tests"
        & python -m unittest discover -s "poe_market_filter_toolkit\tests"

        Write-Section "compileall"
        & python -m compileall "poe_market_filter_toolkit\core" "poe_market_filter_toolkit\scripts"

        Write-Section "git status"
        & git status --short
    }
    "status" {
        Write-Section "git status"
        & git status --short

        Write-Section "recent commits"
        & git log --oneline --decorate -8
    }
    "changed" {
        Write-Section "working tree diff"
        & git diff --stat

        Write-Section "staged diff"
        & git diff --cached --stat
    }
    "artifacts" {
        Write-Section "ignored/untracked artifacts"
        & git ls-files -o -i --exclude-standard | Select-Object -First 200
    }
    "clean" {
        Write-Section "clean local caches"
        & "$Root\tasks.ps1" clean-local
    }
    default {
        Write-Host "Tarefa desconhecida: $Task"
        Write-Host ""
        Show-Help
        exit 1
    }
}

