$url = "http://host.docker.internal:5000"

Write-Host "Phase 1: normal traffic (30s)"
docker run --rm williamyeh/hey -z 30s -c 20 "$url/" | Out-Null

Write-Host "Phase 2: random errors at 40% (45s)"
docker run --rm williamyeh/hey -z 45s -c 20 "$url/aleatoire?taux=40" | Out-Null

Write-Host "Phase 3: latency spike (45s)"
docker run --rm williamyeh/hey -z 45s -c 20 "$url/lent?max=3" | Out-Null

Write-Host "Phase 4: unhandled exceptions burst"
docker run --rm williamyeh/hey -n 300 -c 20 "$url/exception" | Out-Null

Write-Host "Phase 5: 404 flood (not counted as errors)"
docker run --rm williamyeh/hey -z 20s -c 10 "$url/nimportequoi" | Out-Null

Write-Host "Done"