param(
  [string]$Tag = "oss-report-agent:0.1.0",
  [string]$OllamaBaseUrl = "http://127.0.0.1:11434",
  [string]$Model = "llama3.1:8b"
)

docker run --rm -p 8000:8000 `
  -e OLLAMA_BASE_URL=$OllamaBaseUrl `
  -e OLLAMA_MODEL=$Model `
  -v /tmp:/tmp `
  $Tag
