<# IT Solutions Unified Enterprise PowerShell Wrapper #>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)
& "python" "E:\It solution\products\cli.py" @Args
