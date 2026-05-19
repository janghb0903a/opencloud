{{- define "grafana-ai-assistant.fullname" -}}
{{- default .Chart.Name .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
