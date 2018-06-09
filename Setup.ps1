# ----------------------------------------------------------------------
# |  
# |  Setup.ps1
# |  
# |  Michael Sharp <ms@MichaelGSharp.com>
# |      2018-06-07 11:21:37
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright Michael Sharp 2018.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# |  
# |  Run as:
# |     Setup.ps1 [/debug] [/verbose] [/configuration=<config_name>]*
# |  
# ----------------------------------------------------------------------

$env:DEVELOPMENT_ENVIRONMENT_USE_WINDOWS_POWERSHELL=1

function ExitScript {
    Remove-Item "NULL" -ErrorAction SilentlyContinue
    exit
}

if ($env:DEVELOPMENT_ENVIRONMENT_FUNDAMENTAL -eq "") {
    Write-Host  ""
    Write-Error "ERROR: Please run Activate.ps1 within a repository before running this script. It may be necessary to Setup and Activate the Common_Environment repository before setting up this one."
    Write-Host  ""
    
    ExitScript
}

Invoke-Expression "$env:DEVELOPMENT_ENVIRONMENT_FUNDAMENTAL\RepositoryBootstrap\Impl\Setup.cmd '$PSScriptRoot' $args"

ExitScript