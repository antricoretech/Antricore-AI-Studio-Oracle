# Optional source checkout ONLY; GPU model weights are downloaded separately.
param(
 [ValidateSet('ComfyUI','AIToolkit','Flux2','ZImage','Wan22','Wan21','Kokoro','MuseTalk','VHS')]
 [string[]]$Names = @('ComfyUI','Flux2','AIToolkit','Wan22','Kokoro')
)
$ErrorActionPreference='Stop'
$repos = @{
 'ComfyUI' = 'https://github.com/comfy-org/ComfyUI.git'
 'AIToolkit' = 'https://github.com/ostris/ai-toolkit.git'
 'Flux2' = 'https://github.com/black-forest-labs/flux2.git'
 'ZImage' = 'https://github.com/Tongyi-MAI/Z-Image.git'
 'Wan22' = 'https://github.com/Wan-Video/Wan2.2.git'
 'Wan21' = 'https://github.com/Wan-Video/Wan2.1.git'
 'Kokoro' = 'https://github.com/hexgrad/kokoro.git'
 'MuseTalk' = 'https://github.com/TMElyralab/MuseTalk.git'
 'VHS' = 'https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git'
}
$target=Join-Path (Split-Path -Parent $PSScriptRoot) 'external'
New-Item -ItemType Directory -Force $target | Out-Null
foreach($name in $Names) {
 $path=Join-Path $target $name
 if(Test-Path $path) { Write-Host "Skipping existing checkout $name"; continue }
 git clone --depth 1 $repos[$name] $path
 if($LASTEXITCODE -ne 0) { throw "Git clone failed: $name" }
}
Write-Host 'Source cloned. Models/weights must be downloaded separately; licenses still apply.'
